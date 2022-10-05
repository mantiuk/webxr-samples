from threading import Lock
from flask import Flask, render_template, session, request, \
    copy_current_request_context, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

from gfxdisp.specbos import specbos_measure
from gfxdisp.color import *

specbos_port = 'COM3'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
#app.debug = True
socketio = SocketIO(app)

thread = None
thread_lock = Lock()

d_range = range(0, 50, 2) 

meas_d = [100] + list(d_range) + list(d_range)
d_width = [0] + [3] * len(d_range) + [5] * len(d_range)

meas_file = 'vr_contrast_meas_quest2.csv'

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count})

# @app.route('/example')
# def example():
#     return render_template('websocket_example.html', async_mode=socketio.async_mode)

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('', path)

# def index():
#     return send_from_directory('static', 'index.html')

# @app.route('/measure_contrast.html')
# def measure_contrast():
#     return send_from_directory('static', 'measure_contrast.html')

#     #return "<p>Hello, World!</p>"
#     #return render_template('index.html')

def next_measurement():
    if session.get('do_pause', 0) == 1:
        return
    step = session.get('meas_step', -1)    
    if step == -1 or step >= len(meas_d):
        step=-1
    else:                
        print( "step {} out of {}".format(step, len(meas_d)-1) )
        emit('show',
            { 'd_beg': meas_d[step], 'd_end': meas_d[step]+d_width[step], 'r': 1, 'g': 1, 'b': 1, 'step': session['meas_step']})

@socketio.event
def start_measurement(start_from):
    print( f'Starting measurement from {start_from}' )

    session['meas_step'] = int(start_from)
    session['do_pause'] = 0
    next_measurement()

@socketio.event
def pause_measurement(message):
    print( 'Measurements paused' )
    session['do_pause'] = 1

@socketio.event
def single_measurement(message):
    print( 'Single measurement' )
    (Y, x, y) = specbos_measure( specbos_port )
    print( 'Y = {}; x = {}; y = {}'.format( Y, x, y) )

    Yxy = np.array( [[Y, x, y]] )
    sRGB = im_ctrans( Yxy, 'Yxy', 'srgb', exposure=0.5/Y )*255

    emit('measured',
        { 'Y': Y, 'x': x, 'y': y, 'r': sRGB[0,0], 'g': sRGB[0,1], 'b': sRGB[0,2], 'step': -1 })

@socketio.event
def ready_to_measure():
    step = session.get('meas_step', -1)    
    print( 'Measuring {}'.format(step) )
    (Y, x, y) = specbos_measure( specbos_port )
    print( 'd_beg = {}; Y = {}; x = {}; y = {}'.format( meas_d[step], Y, x, y) )

    Yxy = np.array( [[Y, x, y]] )
    sRGB = im_ctrans( Yxy, 'Yxy', 'srgb', exposure=0.5/Y )

    if step==0:
        with open(meas_file, "w") as fo:
            fo.write( "d_beg, d_end, Y, x, y\n" )

    with open(meas_file, "a") as fo:
        d_beg = meas_d[step]
        d_end = meas_d[step] + d_width[step]
        fo.write( f'{d_beg}, {d_end}, {Y}, {x}, {y}\n' )

    step = step+1
    session['meas_step'] = step
    emit('measured',
        { 'Y': Y, 'x': x, 'y': y, 'r': sRGB[0,0], 'g': sRGB[0,1], 'b': sRGB[0,2], 'step': step })
    next_measurement()


@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


# @socketio.event
# def my_broadcast_event(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': message['data'], 'count': session['receive_count']},
#          broadcast=True)


# @socketio.event
# def join(message):
#     join_room(message['room'])
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': 'In rooms: ' + ', '.join(rooms()),
#           'count': session['receive_count']})


# @socketio.event
# def leave(message):
#     leave_room(message['room'])
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': 'In rooms: ' + ', '.join(rooms()),
#           'count': session['receive_count']})


# @socketio.on('close_room')
# def on_close_room(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
#                          'count': session['receive_count']},
#          to=message['room'])
#     close_room(message['room'])


# @socketio.event
# def my_room_event(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': message['data'], 'count': session['receive_count']},
#          to=message['room'])


# @socketio.event
# def disconnect_request():
#     @copy_current_request_context
#     def can_disconnect():
#         disconnect()

#     session['receive_count'] = session.get('receive_count', 0) + 1
#     # for this emit we use a callback function
#     # when the callback function is invoked we know that the message has been
#     # received and it is safe to disconnect
#     emit('my_response',
#          {'data': 'Disconnected!', 'count': session['receive_count']},
#          callback=can_disconnect)


# @socketio.event
# def my_ping():
#     emit('my_pong')


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app)


# @socketio.on('my event')
# def test_message(message):
#     emit('my response', {'data': message['data']})

# @socketio.on('my broadcast event')
# def test_message(message):
#     emit('my response', {'data': message['data']}, broadcast=True)

# @socketio.on('connect')
# def test_connect():
#     emit('my response', {'data': 'Connected'})

# @socketio.on('disconnect')
# def test_disconnect():
#     print('Client disconnected')

# if __name__ == '__main__':
#     socketio.run(app)
