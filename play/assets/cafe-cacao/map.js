/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Un solo mapa. Sara puede cambiar el SVG o el PNG del mismo nombre.
   El juego no tiene que tocarse. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.CAFE_CACAO_ART = api;
})(typeof window !== 'undefined' ? window : this, function () {
  return {
    base: 'assets/cafe-cacao/',
    icons: {
      cafe: 'cafe.svg',
      cacao: 'cacao.svg',
      bag: 'bulto.svg',
      oro: 'moneda-oro.svg',
      plata: 'moneda-plata.svg',
      cobre: 'moneda-cobre.svg',
      ingot: 'lingote.svg',
      workshopCafe: 'taller-cafe.svg',
      workshopCacao: 'taller-cacao.svg',
      shade: 'sombra.svg',
      cherry: 'cereza.svg',
      pod: 'mazorca.svg',
      libro: 'libro.svg',
      patio: 'patio.svg',
    },
    colors: {
      trunk: '#6b4228',
      trunkDark: '#5a3a24',
      leaf: '#2f6b3a',
      leafDeep: '#1f5a34',
      leafLite: '#3e7d46',
      shade: '#1e4d32',
      shadeDeep: '#163c28',
      cherry: '#d23b32',
      cherryDark: '#a82420',
      pod: '#e2a322',
      podRipe: '#d4552a',
      soil: '#6a4a32',
      wall: '#c4a574',
      roof: '#8c4a32',
      patio: '#d7c39a',
      tank: '#6f8494',
      roaster: '#3a342c',
      ember: '#ff8a3d',
      plotEmpty: '#8a6244',
      seedling: '#8fbf63',
      green: '#2f7a3a',
      pulp: '#f3efe4',
      dry: '#e6d7a8',
      box: '#6a4a2c',
      signPost: '#6b4228',
    },
  };
});
