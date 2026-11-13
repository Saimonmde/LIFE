/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Local glTF 2.0 binary loader. three.module.js does not ship GLTFLoader, and nothing is loaded from a CDN.
import * as T from './three.module.js';

const COMP = { 5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4 };
const TYPE_N = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };

export class GLTFLoader {
  load(url, onLoad, _onProgress, onError) {
    fetch(url).then(r => {
      if (!r.ok) throw new Error('GLB ' + r.status + ' ' + url);
      return r.arrayBuffer();
    }).then(buf => this.parse(buf)).then(onLoad).catch(err => {
      if (onError) onError(err);
      else console.error(err);
    });
  }
  parse(buffer) {
    const view = new DataView(buffer);
    if (view.getUint32(0, true) !== 0x46546C67) throw new Error('no es GLB');
    let offset = 12;
    let json, bin;
    while (offset + 8 <= buffer.byteLength) {
      const len = view.getUint32(offset, true);
      const type = view.getUint32(offset + 4, true);
      const chunk = new Uint8Array(buffer, offset + 8, len);
      if (type === 0x4E4F534A) json = JSON.parse(new TextDecoder().decode(chunk));
      else if (type === 0x004E4942) bin = chunk;
      offset += 8 + len;
    }
    if (!json || !bin) throw new Error('GLB incompleto');
    const acc = json.accessors || [];
    const views = json.bufferViews || [];
    function read(index) {
      const a = acc[index], bv = views[a.bufferView];
      const n = TYPE_N[a.type], size = COMP[a.componentType];
      const start = (bv.byteOffset || 0) + (a.byteOffset || 0);
      const count = a.count * n;
      if (a.componentType === 5126) return new Float32Array(bin.buffer, bin.byteOffset + start, count);
      if (a.componentType === 5123) return new Uint16Array(bin.buffer, bin.byteOffset + start, count);
      if (a.componentType === 5125) return new Uint32Array(bin.buffer, bin.byteOffset + start, count);
      throw new Error('componente GLB no soportado');
    }
    const scene = new T.Group();
    const pending = [];
    for (const node of json.nodes || []) {
      if (node.mesh == null) continue;
      for (const prim of json.meshes[node.mesh].primitives || []) {
      const geo = new T.BufferGeometry();
      const pos = read(prim.attributes.POSITION);
      geo.setAttribute('position', new T.BufferAttribute(pos, 3));
      if (prim.attributes.NORMAL != null) geo.setAttribute('normal', new T.BufferAttribute(read(prim.attributes.NORMAL), 3));
      else geo.computeVertexNormals();
      if (prim.attributes.COLOR_0 != null) geo.setAttribute('color', new T.BufferAttribute(read(prim.attributes.COLOR_0), 3));
      if (prim.attributes.TEXCOORD_0 != null) geo.setAttribute('uv', new T.BufferAttribute(read(prim.attributes.TEXCOORD_0), 2));
      if (prim.indices != null) geo.setIndex(new T.BufferAttribute(read(prim.indices), 1));
      const pbr = (json.materials && json.materials[prim.material || 0] && json.materials[prim.material || 0].pbrMetallicRoughness) || {};
      const factor = pbr.baseColorFactor || [0.84, 0.83, 0.8, 1];
      const mat = new T.MeshLambertMaterial({
        color: new T.Color(factor[0], factor[1], factor[2]),
        vertexColors: prim.attributes.COLOR_0 != null,
        side: T.DoubleSide,
      });
      const mesh = new T.Mesh(geo, mat);
      if (node.matrix) mesh.applyMatrix4(new T.Matrix4().fromArray(node.matrix));
      else {
        if (node.translation) mesh.position.fromArray(node.translation);
        if (node.rotation) mesh.quaternion.fromArray(node.rotation);
        if (node.scale) mesh.scale.fromArray(node.scale);
      }
      mesh.castShadow = mesh.receiveShadow = true;
      const image = json.images && json.images[0];
      const texView = image && views[image.bufferView];
      if (texView) {
        const bytes = bin.slice(texView.byteOffset || 0, (texView.byteOffset || 0) + texView.byteLength);
        const url = URL.createObjectURL(new Blob([bytes], { type: image.mimeType || 'image/jpeg' }));
        pending.push(new Promise((ok, ko) => {
          const img = new Image();
          img.onload = () => {
            const tex = new T.Texture(img);
            tex.colorSpace = T.SRGBColorSpace;
            tex.flipY = false;
            tex.needsUpdate = true;
            mat.map = tex;
            mat.color.set('#ffffff');
            mat.needsUpdate = true;
            URL.revokeObjectURL(url);
            ok();
          };
          img.onerror = () => { URL.revokeObjectURL(url); ko(new Error('textura')); };
          img.src = url;
        }));
      }
      scene.add(mesh);
      }
    }
    return Promise.all(pending).then(() => ({ scene }));
  }
}
