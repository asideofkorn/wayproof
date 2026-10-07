/* Text discovery only: a match never establishes permission or feasibility. */
const WayproofSearch = {
  tokens(text) {
    return (text.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [])
      .map(word => ["dog", "dogs", "pets"].includes(word) ? "pet" : word);
  },
  matches(text, query) {
    const words = this.tokens(text);
    return this.tokens(query).every(term => words.some(word => word.startsWith(term)));
  },
};
if (typeof module !== "undefined") module.exports = WayproofSearch;
