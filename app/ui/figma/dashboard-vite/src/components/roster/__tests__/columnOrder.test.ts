import { applyOrder, defaultKeys, findGroupRange, moveGroup } from '../../../utils/columnOrder';

describe('columnOrder utilities', () => {
  const testColumns = [
    { key: 'name', group: 'CORE', fixed: true },
    { key: 'ovr', group: 'CORE' },
    { key: 'spd', group: 'CORE' },
    { key: 'cmp', group: 'QB' },
    { key: 'att', group: 'QB' },
    { key: 'yds', group: 'QB' },
    { key: 'rush', group: 'RB' },
    { key: 'rec', group: 'REC' },
  ];

  describe('applyOrder', () => {
    it('should reorder columns based on provided keys', () => {
      const newOrder = ['name', 'cmp', 'att', 'yds', 'ovr', 'spd', 'rush', 'rec'];
      const result = applyOrder(testColumns, newOrder);
      expect(result.map(c => c.key)).toEqual(newOrder);
    });

    it('should append unknown keys at the end', () => {
      const newOrder = ['name', 'cmp', 'att', 'unknown1', 'unknown2'];
      const result = applyOrder(testColumns, newOrder);
      expect(result.map(c => c.key)).toEqual([
        'name', 'cmp', 'att', 'ovr', 'spd', 'yds', 'rush', 'rec'
      ]);
    });

    it('should handle empty keys array', () => {
      const result = applyOrder(testColumns, []);
      expect(result).toEqual(testColumns);
    });
  });

  describe('defaultKeys', () => {
    it('should return array of column keys in original order', () => {
      const result = defaultKeys(testColumns);
      expect(result).toEqual(['name', 'ovr', 'spd', 'cmp', 'att', 'yds', 'rush', 'rec']);
    });
  });

  describe('findGroupRange', () => {
    it('should find correct range for QB group', () => {
      const range = findGroupRange(testColumns, 3); // 'cmp' index
      expect(range).toEqual({ start: 3, end: 5 });
    });

    it('should find correct range for single column group', () => {
      const range = findGroupRange(testColumns, 6); // 'rush' index
      expect(range).toEqual({ start: 6, end: 6 });
    });

    it('should return null for column without group', () => {
      const columnsWithoutGroup = [
        { key: 'name' },
        { key: 'ovr', group: 'CORE' },
      ];
      const range = findGroupRange(columnsWithoutGroup, 0);
      expect(range).toBeNull();
    });
  });

  describe('moveGroup', () => {
    it('should move single column when no group', () => {
      const result = moveGroup(testColumns, 6, 2); // move 'rush' to position 2
      expect(result.map(c => c.key)).toEqual([
        'name', 'ovr', 'rush', 'spd', 'cmp', 'att', 'yds', 'rec'
      ]);
    });

    it('should move entire QB group', () => {
      const result = moveGroup(testColumns, 3, 0); // move QB group to start (after name)
      expect(result.map(c => c.key)).toEqual([
        'name', 'cmp', 'att', 'yds', 'ovr', 'spd', 'rush', 'rec'
      ]);
    });

    it('should handle moving group to end', () => {
      const result = moveGroup(testColumns, 3, 7); // move QB group to end
      expect(result.map(c => c.key)).toEqual([
        'name', 'ovr', 'spd', 'rush', 'rec', 'cmp', 'att', 'yds'
      ]);
    });

    it('should not move fixed column', () => {
      const result = moveGroup(testColumns, 0, 4); // try to move 'name'
      expect(result.map(c => c.key)).toEqual([
        'name', 'ovr', 'spd', 'cmp', 'att', 'yds', 'rush', 'rec'
      ]);
    });
  });
});
