/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Mapa único del arte de Sara para café, cacao, talleres y el Libro Mayor.
   El juego pide estos nombres. Para cambiar un dibujo, se reemplaza el archivo.
   Sara deja en v2/ los mismos nombres, de pie y sin texto:
   v2/taller_cafe_lite.png, v2/taller_cacao_lite.png, v2/kg_cosechados.svg.
   Si el archivo no está, o si sigue siendo una hoja apaisada, se usa el de ahora.
   Las hojas 16:9 quedan en hojas/. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.CAFE_CACAO_ART = api;
})(typeof window !== 'undefined' ? window : this, function () {
  return {
    base: 'assets/cafe-cacao/',
    v2: 'v2/',
    credit: 'Sara',
    stand: {
      workshopCafe: 'taller_cafe_lite.png',
      workshopCacao: 'taller_cacao_lite.png',
      kg: 'kg_cosechados.svg',
    },
    sheets: {
      workshopCafe: 'hojas/taller_cafe_lite.png',
      workshopCacao: 'hojas/taller_cacao_lite.png',
    },
    icons: {
      cafe: 'cafe.svg',
      cacao: 'cacao.svg',
      bag: 'bulto.svg',
      kg: 'kg_cosechados.svg',
      oro: 'simoncoin.svg',
      plata: 'simonplata.svg',
      cobre: 'simonchis.svg',
      ingot: 'lingote.svg',
      workshopCafe: 'taller_cafe_lite.png',
      workshopCacao: 'taller_cacao_lite.png',
      plotCafePlanton: 'cafe_siembra_64.png',
      plotCafeVerde: 'cafe_crecimiento_64.png',
      plotCafeMaduro: 'cafe_cosecha_64.png',
      plotCacaoPlanton: 'cacao_siembra_64.png',
      plotCacaoVerde: 'cacao_crecimiento_64.png',
      plotCacaoMaduro: 'cacao_cosecha_64.png',
      bagCafe: 'bulto_cafe_64.png',
      bagCacao: 'bulto_cacao_64.png',
    },
    models: {
      plant: {
        cafe: {
          siembra: { glb: '', lod: '', flat: 'cafe_siembra_64.png' },
          crecimiento: { glb: '', lod: '', flat: 'cafe_crecimiento_64.png' },
          floracion: { glb: '', lod: '', flat: 'cafe_crecimiento_64.png' },
          fruto: { glb: '', lod: '', flat: 'cafe_cosecha_64.png' },
          cosecha: { glb: '', lod: '', flat: 'cafe_cosecha_64.png' },
        },
        cacao: {
          siembra: { glb: '', lod: '', flat: 'cacao_siembra_64.png' },
          crecimiento: { glb: '', lod: '', flat: 'cacao_crecimiento_64.png' },
          floracion: { glb: '', lod: '', flat: 'cacao_crecimiento_64.png' },
          fruto: { glb: '', lod: '', flat: 'cacao_cosecha_64.png' },
          cosecha: { glb: '', lod: '', flat: 'cacao_cosecha_64.png' },
        },
      },
      workshop: {
        cafe: {
          despulpado: { glb: '', lod: '', flat: 'taller_cafe_lite.png' },
          fermentacion: { glb: '', lod: '', flat: 'taller_cafe_lite.png' },
          lavado: { glb: '', lod: '', flat: 'taller_cafe_lite.png' },
          secado: { glb: '', lod: '', flat: 'taller_cafe_lite.png' },
          trilla: { glb: '', lod: '', flat: 'taller_cafe_lite.png' },
          bulto: { glb: '', lod: '', flat: 'bulto_cafe_64.png' },
        },
        cacao: {
          quiebre: { glb: '', lod: '', flat: 'taller_cacao_lite.png' },
          fermentacion: { glb: '', lod: '', flat: 'taller_cacao_lite.png' },
          secado: { glb: '', lod: '', flat: 'taller_cacao_lite.png' },
          seleccion: { glb: '', lod: '', flat: 'taller_cacao_lite.png' },
          libro: { glb: '', lod: '', flat: 'kg_cosechados.svg' },
        },
      },
    },
    colors: {
      trunk: '#6b4a2c',
      trunkDark: '#3a2412',
      leaf: '#2f6a32',
      leafDeep: '#1a4a2c',
      leafLite: '#547a4b',
      shade: '#1e5a32',
      shadeDeep: '#1a4a2c',
      cherry: '#c23b2e',
      cherryDark: '#8a1e1a',
      pod: '#e5a02a',
      podRipe: '#c45a2a',
      soil: '#5a3a22',
      wall: '#f3ead7',
      roof: '#a85a3a',
      patio: '#d7c39a',
      tank: '#6f8494',
      roaster: '#3a342c',
      ember: '#d4a23a',
      plotEmpty: '#7a5330',
      seedling: '#8ccf4a',
      green: '#7a9a3a',
      pulp: '#f3ead7',
      dry: '#c4a574',
      box: '#6b4a2c',
      signPost: '#6b4a2c',
    },
  };
});
