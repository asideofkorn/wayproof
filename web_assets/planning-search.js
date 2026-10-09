/* Text discovery only: a match never establishes permission or feasibility. */
const WayproofSearch = {
  tokens(text) {
    return (text.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [])
      .map(word => ["dog", "dogs", "pets"].includes(word) ? "pet" : word);
  },
  discover(row, query, kind) {
    return this.matches(row.text, query) && (!kind || row.kind === kind) &&
      (!row.parents.length || kind === row.kind || /\d/.test(query) ||
       row.name.toLocaleLowerCase() === query.toLocaleLowerCase() ||
       (this.matches(row.name, query) && !row.parents.some(p => this.matches(p.name, query))));
  },
  matches(text, query) {
    const words = this.tokens(text);
    return this.tokens(query).every(term => words.some(word =>
      term === "pet" ? word === term : word.startsWith(term)));
  },
};
if (typeof module !== "undefined") module.exports = WayproofSearch;
