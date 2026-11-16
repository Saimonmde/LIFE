/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Mapa único del arte de Sara para café, cacao, talleres y el Libro Mayor.
   El juego pide estos nombres. Para cambiar un dibujo, se reemplaza el archivo.
   Los talleres de pie y el kg legible ya están en estos nombres (512×512, fondo
   transparente). Las anclas del pie están en v2/anclas.json. Las hojas 16:9
   viejas quedan en hojas/. El lingote no cambió. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.CAFE_CACAO_ART = api;
})(typeof window !== 'undefined' ? window : this, function () {
  return {
    base: 'assets/cafe-cacao/',
    v2: 'v2/',
    rev: 'v2-r1',
    credit: 'Sara',
    anchors: 'v2/anclas.json',
    stand: {
      workshopCafe: 'taller_cafe_lite.png',
      workshopCacao: 'taller_cacao_lite.png',
      kg: 'kg_cosechados.svg',
    },
    sheets: {
      workshopCafe: 'hojas/taller_cafe_lite.png',
      workshopCacao: 'hojas/taller_cacao_lite.png',
    },
    sara: 'sara/',
    manifest: 'sara/manifest.json',
    stageIcons: {
      cafe: [
        { id: 'siembra', label: 'Siembra', file: 'sara/iconos-etapas/64/cafe_01_siembra.png', live: 'cafe_siembra_64.png' },
        { id: 'crecimiento', label: 'Crecimiento', file: 'sara/iconos-etapas/64/cafe_02_crecimiento.png', live: 'cafe_crecimiento_64.png' },
        { id: 'floracion', label: 'Floración', file: 'sara/iconos-etapas/64/cafe_03_floracion.png', live: 'cafe_crecimiento_64.png' },
        { id: 'fruto', label: 'Cereza', file: 'sara/iconos-etapas/64/cafe_04_cereza_madura.png', live: 'cafe_cosecha_64.png' },
        { id: 'cosecha', label: 'Cosecha', file: 'sara/iconos-etapas/64/cafe_05_cosecha.png', live: 'cafe_cosecha_64.png' },
      ],
      cacao: [
        { id: 'siembra', label: 'Siembra', file: 'sara/iconos-etapas/64/cacao_01_siembra.png', live: 'cacao_siembra_64.png' },
        { id: 'crecimiento', label: 'Crecimiento', file: 'sara/iconos-etapas/64/cacao_02_crecimiento.png', live: 'cacao_crecimiento_64.png' },
        { id: 'floracion', label: 'Floración', file: 'sara/iconos-etapas/64/cacao_03_floracion.png', live: 'cacao_crecimiento_64.png' },
        { id: 'fruto', label: 'Mazorca', file: 'sara/iconos-etapas/64/cacao_04_mazorca.png', live: 'cacao_cosecha_64.png' },
        { id: 'cosecha', label: 'Cosecha', file: 'sara/iconos-etapas/64/cacao_05_cosecha.png', live: 'cacao_cosecha_64.png' },
      ],
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
