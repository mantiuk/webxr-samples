import { Material } from "../core/material.js";
import { Node } from "../core/node.js";
import { PrimitiveStream } from "../geometry/primitive-stream.js";
import { UrlTexture } from "../core/texture.js";

class ShaderConeMaterial extends Material {
  constructor() {
    super();

    this.state.blend = true;
    this.icon = this.defineSampler("icon");
  }

  get materialName() {
    return "CUSTOM_SHADER_MATERIAL";
  }

  get vertexSource() {
    return `
    attribute vec3 POSITION;
    attribute vec2 TEXCOORD_0;

    varying vec2 vTexCoord;

    vec4 vertex_main(mat4 proj, mat4 view, mat4 model) {
      vTexCoord = TEXCOORD_0;
      vec4 pos = vec4(POSITION.x, POSITION.y, POSITION.z, 1.0);
      return proj * view * model * pos;
    }`;
  }

  get fragmentSource() {
    return `
    uniform sampler2D icon;
    varying vec2 vTexCoord;

    vec4 fragment_main() {
      //vec4 fake = texture2D(icon, -vTexCoord);
      float r = 1.-pow((vTexCoord.x-0.5)*(vTexCoord.x-0.5) + (vTexCoord.y-0.5)*(vTexCoord.y-0.5),0.2);
      return vec4( r, r, r, 1. ); 
    }`;
  }
}
  

class ShaderRingMaterial extends Material {
    constructor() {
      super();
  
      this.state.blend = true;
      this.icon = this.defineSampler("icon");
      this.defineUniform('ring_start', 0.);
      this.defineUniform('ring_end', 0.1);
      this.defineUniform('is_centering', 1.);
      this.defineUniform('color', [1., 1., 1.]);
    }
  
    get materialName() {
      return "CUSTOM_SHADER_MATERIAL";
    }
  
    get vertexSource() {
      return `
      attribute vec3 POSITION;
      attribute vec2 TEXCOORD_0;
  
      varying vec2 vTexCoord;
  
      vec4 vertex_main(mat4 proj, mat4 view, mat4 model) {
        vTexCoord = TEXCOORD_0;
        vec4 pos = vec4(POSITION.x, POSITION.y, POSITION.z, 1.0);
        return proj * view * model * pos;
      }`;
    }
  
    get fragmentSource() {
      return `
      uniform sampler2D icon;
      varying vec2 vTexCoord;

      uniform float ring_start;
      uniform float ring_end;
      uniform float is_centering;
      uniform vec3 color;

      vec4 fragment_main() {
        //vec4 fake = texture2D(icon, -vTexCoord);
        float r = sqrt((vTexCoord.x-0.5)*(vTexCoord.x-0.5) + (vTexCoord.y-0.5)*(vTexCoord.y-0.5));
        vec4 out_color;
        if( is_centering==1. ) {
          float p = pow( 1.-r, 3. );
          out_color = vec4(p,p,p,1.);
        } else {
          float p = float((r>=ring_start) && (r<=ring_end));
          out_color = vec4( p*color.r, p*color.g, p*color.b, 1. );
        }
        return out_color;
      }`;
    }
  }
  

export class QuadShaderNode extends Node {
  constructor(texturePath, textureSize, selectable=false) {
    super();

    this.selectable = selectable;
    this._textureSize = textureSize;
    this._iconTexture = new UrlTexture(texturePath);
    this.ring = 1;
    this.ringMaterial = null;
  }

  nextRing() {
      this.ring++;
      if( this._iconRenderPrimitive ) {
            let deg = this.ring;
            let x_beg = (Math.tan(deg * Math.PI / 180) * 3) / this._textureSize;
            let x_end = (Math.tan((deg+1) * Math.PI / 180) * 3) / this._textureSize;
            this._iconRenderPrimitive.uniforms.ring_start.value = x_beg;
            this._iconRenderPrimitive.uniforms.ring_end.value = x_end;
      }
      console.log( "Ring: " + this.ring );
  }

  setRing( d_beg, d_end, rgb ) {
    let x_beg = (Math.tan(d_beg * Math.PI / 180) * 3) / this._textureSize;
    let x_end = (Math.tan(d_end * Math.PI / 180) * 3) / this._textureSize;
    this._iconRenderPrimitive.uniforms.ring_start.value = x_beg;
    this._iconRenderPrimitive.uniforms.ring_end.value = x_end;
    this._iconRenderPrimitive.uniforms.color.value = rgb;
    this._iconRenderPrimitive.uniforms.is_centering = 0;
  }

  setCentering() {
    this._iconRenderPrimitive.uniforms.is_centering = 1;
  }

  onRendererChanged(renderer) {
    let stream = new PrimitiveStream();
    let hs = this._textureSize * 0.5;
    stream.clear();
    stream.startGeometry();

    stream.pushVertex(-hs, hs, 0, 0, 0, 0, 0, 1);
    stream.pushVertex(-hs, -hs, 0, 0, 1, 0, 0, 1);
    stream.pushVertex(hs, -hs, 0, 1, 1, 0, 0, 1);
    stream.pushVertex(hs, hs, 0, 1, 0, 0, 0, 1);

    stream.pushTriangle(0, 1, 2);
    stream.pushTriangle(0, 2, 3);

    stream.endGeometry();

    let iconPrimitive = stream.finishPrimitive(renderer);
    this.ringMaterial = new ShaderRingMaterial();
    this.ringMaterial.icon.texture = this._iconTexture;
    this._iconRenderPrimitive = renderer.createRenderPrimitive(
      iconPrimitive,
      this.ringMaterial
    );
    this.addRenderPrimitive(this._iconRenderPrimitive);
  }
}
