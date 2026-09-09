// Mock Stats API for NFL simulation game - Comprehensive Stats

export type StatPeriod = 'per_game' | 'season' | 'career';
export type StatView = 'raw' | 'rate';

// Comprehensive player stats interface
export interface ComprehensivePlayerStats {
  id: string;
  name: string;
  team: string;
  position: string;
  age: number;
  
  // Availability & Participation
  availability: {
    games_played: number;
    games_started: number;
    snaps_off: number;
    snaps_def: number;
    snaps_st: number;
  };
  
  // Offense - Passing
  passing?: {
    pass_att: number;
    pass_cmp: number;
    pass_yds: number;
    pass_td: number;
    pass_int: number;
    sacks_taken: number;
    air_yds: number;
    yac_gained: number;
    throwaways: number;
    spikes: number;
    batted_passes: number;
    drops_forced: number;
    play_action_att: number;
    screen_att: number;
    deep_att: number;
    pressure_dropbacks: number;
    hits_on_qb: number;
  };
  
  // Offense - Rushing
  rushing?: {
    rush_att: number;
    rush_yds: number;
    rush_td: number;
    yards_before_contact: number;
    yards_after_contact: number;
    designed_rush_att: number;
    scramble_att: number;
  };
  
  // Offense - Receiving
  receiving?: {
    tar: number;
    rec: number;
    rec_yds: number;
    rec_td: number;
    air_yds_for: number;
    yac: number;
    drops: number;
    contested_catches_won: number;
    receptions_deep: number;
  };
  
  // Ball Security
  ball_security?: {
    fumbles: number;
    fumbles_lost: number;
  };
  
  // Defense - Tackling
  defense_tackling?: {
    tackles: number;
    assists: number;
    missed_tackles: number;
    tfl: number;
  };
  
  // Defense - Pass Rush
  defense_pass_rush?: {
    sacks: number;
    qb_hits: number;
    pressures: number;
    hurries: number;
    chases: number;
  };
  
  // Defense - Coverage/Turnovers
  defense_coverage?: {
    ints: number;
    pbus: number;
    ff: number;
    fr: number;
    td_def: number;
    targets_defended: number;
    receptions_allowed: number;
    rec_yds_allowed: number;
    yacs_allowed: number;
    penalties_committed_def: number;
  };
  
  // Special Teams - Kicking
  kicking?: {
    fg_made: number;
    fg_att: number;
    xp_made: number;
    xp_att: number;
    long_fg_made: number;
  };
  
  // Special Teams - Punting
  punting?: {
    punts: number;
    punt_yds: number;
    long_punt: number;
    punts_inside_20: number;
    punt_touchbacks: number;
    punt_returns_allowed: number;
    punt_return_yds_allowed: number;
  };
  
  // Special Teams - Kickoffs
  kickoffs?: {
    kickoffs: number;
    touchbacks: number;
    avg_kickoff_yds: number;
    kickoff_returns_allowed: number;
    kickoff_return_yds_allowed: number;
  };
  
  // Special Teams - Returns & Coverage
  returns?: {
    kr: number;
    kr_yds: number;
    kr_td: number;
    pr: number;
    pr_yds: number;
    pr_td: number;
    st_tackles: number;
    st_missed_tackles: number;
    st_forced_fumbles: number;
    st_fumble_recoveries: number;
  };
  
  // Discipline
  discipline: {
    penalties: number;
    penalty_yds: number;
  };
}

// Rate stats computed from raw stats
export interface RateStats {
  // General
  snap_share_off?: number;
  snap_share_def?: number;
  snap_share_st?: number;
  games_active_pct?: number;
  starts_rate?: number;
  
  // Passing rates
  cmp_pct?: number;
  yds_per_att?: number;
  yds_per_cmp?: number;
  td_pct?: number;
  int_pct?: number;
  sack_rate?: number;
  air_yds_share?: number;
  yac_share?: number;
  deep_att_rate?: number;
  play_action_rate?: number;
  screen_rate?: number;
  pressure_rate?: number;
  hit_rate?: number;
  throwaway_rate?: number;
  batted_rate?: number;
  drop_rate_against_qb?: number;
  passer_rating?: number;
  
  // Rushing rates
  yds_per_rush?: number;
  td_rate_rush?: number;
  yards_before_contact_per_att?: number;
  yards_after_contact_per_att?: number;
  designed_rush_share?: number;
  scramble_share?: number;
  
  // Receiving rates
  catch_pct?: number;
  yds_per_rec?: number;
  yds_per_target?: number;
  td_per_target?: number;
  air_yds_share_for?: number;
  yac_per_rec?: number;
  contested_catch_rate?: number;
  deep_target_rate?: number;
  
  // Ball security rates
  fumbles_per_touch?: number;
  lost_fumbles_per_touch?: number;
  
  // Defense rates
  tackles_per_game?: number;
  missed_tackle_rate?: number;
  pressures_per_pass_snap?: number;
  pressure_conversion_rate?: number;
  ints_per_game?: number;
  pbus_per_game?: number;
  takeaways?: number;
  comp_allowed_pct?: number;
  yards_per_target_allowed?: number;
  yacs_allowed_per_rec?: number;
  penalty_rate_def?: number;
  
  // Special teams rates
  fg_pct?: number;
  xp_pct?: number;
  avg_fg_distance_made?: number;
  gross_punt_avg?: number;
  net_punt_avg?: number;
  inside_20_rate?: number;
  punt_touchback_rate?: number;
  touchback_rate?: number;
  avg_kickoff_depth?: number;
  kr_avg?: number;
  pr_avg?: number;
  return_td_rate?: number;
  st_tackle_rate?: number;
  st_missed_tackle_rate?: number;
}

// Mock season stats data
const SEASON_STATS: ComprehensivePlayerStats[] = [
  // QB - Mac Jones
  {
    id: 'p1',
    name: 'Mac Jones',
    team: 'NE',
    position: 'QB',
    age: 25,
    availability: {
      games_played: 17,
      games_started: 17,
      snaps_off: 1089,
      snaps_def: 0,
      snaps_st: 0,
    },
    passing: {
      pass_att: 521,
      pass_cmp: 352,
      pass_yds: 3801,
      pass_td: 22,
      pass_int: 14,
      sacks_taken: 28,
      air_yds: 2850,
      yac_gained: 951,
      throwaways: 15,
      spikes: 8,
      batted_passes: 12,
      drops_forced: 18,
      play_action_att: 104,
      screen_att: 52,
      deep_att: 68,
      pressure_dropbacks: 142,
      hits_on_qb: 35,
    },
    rushing: {
      rush_att: 32,
      rush_yds: 98,
      rush_td: 1,
      yards_before_contact: 45,
      yards_after_contact: 53,
      designed_rush_att: 8,
      scramble_att: 24,
    },
    ball_security: {
      fumbles: 5,
      fumbles_lost: 2,
    },
    discipline: {
      penalties: 3,
      penalty_yds: 15,
    },
  },
  
  // RB - Rhamondre Stevenson
  {
    id: 'p2',
    name: 'Rhamondre Stevenson',
    team: 'NE',
    position: 'RB',
    age: 25,
    availability: {
      games_played: 16,
      games_started: 14,
      snaps_off: 623,
      snaps_def: 0,
      snaps_st: 12,
    },
    rushing: {
      rush_att: 231,
      rush_yds: 1040,
      rush_td: 9,
      yards_before_contact: 520,
      yards_after_contact: 520,
      designed_rush_att: 231,
      scramble_att: 0,
    },
    receiving: {
      tar: 49,
      rec: 38,
      rec_yds: 238,
      rec_td: 1,
      air_yds_for: 89,
      yac: 149,
      drops: 3,
      contested_catches_won: 2,
      receptions_deep: 1,
    },
    ball_security: {
      fumbles: 3,
      fumbles_lost: 1,
    },
    returns: {
      kr: 2,
      kr_yds: 48,
      kr_td: 0,
      pr: 0,
      pr_yds: 0,
      pr_td: 0,
      st_tackles: 1,
      st_missed_tackles: 0,
      st_forced_fumbles: 0,
      st_fumble_recoveries: 0,
    },
    discipline: {
      penalties: 2,
      penalty_yds: 10,
    },
  },
  
  // WR - DeVante Parker
  {
    id: 'p3',
    name: 'DeVante Parker',
    team: 'NE',
    position: 'WR',
    age: 30,
    availability: {
      games_played: 14,
      games_started: 11,
      snaps_off: 487,
      snaps_def: 0,
      snaps_st: 8,
    },
    receiving: {
      tar: 85,
      rec: 51,
      rec_yds: 588,
      rec_td: 3,
      air_yds_for: 412,
      yac: 176,
      drops: 4,
      contested_catches_won: 12,
      receptions_deep: 8,
    },
    ball_security: {
      fumbles: 1,
      fumbles_lost: 0,
    },
    discipline: {
      penalties: 1,
      penalty_yds: 10,
    },
  },
  
  // TE - Hunter Henry
  {
    id: 'p4',
    name: 'Hunter Henry',
    team: 'NE',
    position: 'TE',
    age: 28,
    availability: {
      games_played: 17,
      games_started: 17,
      snaps_off: 756,
      snaps_def: 0,
      snaps_st: 5,
    },
    receiving: {
      tar: 48,
      rec: 31,
      rec_yds: 419,
      rec_td: 2,
      air_yds_for: 298,
      yac: 121,
      drops: 2,
      contested_catches_won: 5,
      receptions_deep: 3,
    },
    ball_security: {
      fumbles: 0,
      fumbles_lost: 0,
    },
    discipline: {
      penalties: 3,
      penalty_yds: 25,
    },
  },
  
  // LB - Matthew Judon
  {
    id: 'p5',
    name: 'Matthew Judon',
    team: 'NE',
    position: 'LB',
    age: 31,
    availability: {
      games_played: 17,
      games_started: 17,
      snaps_off: 0,
      snaps_def: 812,
      snaps_st: 15,
    },
    defense_tackling: {
      tackles: 62,
      assists: 20,
      missed_tackles: 8,
      tfl: 12,
    },
    defense_pass_rush: {
      sacks: 15.5,
      qb_hits: 28,
      pressures: 68,
      hurries: 32,
      chases: 12,
    },
    defense_coverage: {
      ints: 2,
      pbus: 4,
      ff: 4,
      fr: 1,
      td_def: 1,
      targets_defended: 6,
      receptions_allowed: 8,
      rec_yds_allowed: 45,
      yacs_allowed: 12,
      penalties_committed_def: 5,
    },
    returns: {
      kr: 0,
      kr_yds: 0,
      kr_td: 0,
      pr: 0,
      pr_yds: 0,
      pr_td: 0,
      st_tackles: 2,
      st_missed_tackles: 0,
      st_forced_fumbles: 0,
      st_fumble_recoveries: 0,
    },
    discipline: {
      penalties: 8,
      penalty_yds: 60,
    },
  },
  
  // S - Kyle Dugger
  {
    id: 'p6',
    name: 'Kyle Dugger',
    team: 'NE',
    position: 'S',
    age: 27,
    availability: {
      games_played: 17,
      games_started: 17,
      snaps_off: 0,
      snaps_def: 978,
      snaps_st: 45,
    },
    defense_tackling: {
      tackles: 92,
      assists: 28,
      missed_tackles: 12,
      tfl: 5,
    },
    defense_pass_rush: {
      sacks: 2.0,
      qb_hits: 4,
      pressures: 12,
      hurries: 6,
      chases: 2,
    },
    defense_coverage: {
      ints: 4,
      pbus: 9,
      ff: 2,
      fr: 2,
      td_def: 1,
      targets_defended: 38,
      receptions_allowed: 28,
      rec_yds_allowed: 312,
      yacs_allowed: 89,
      penalties_committed_def: 3,
    },
    returns: {
      kr: 0,
      kr_yds: 0,
      kr_td: 0,
      pr: 0,
      pr_yds: 0,
      pr_td: 0,
      st_tackles: 8,
      st_missed_tackles: 1,
      st_forced_fumbles: 1,
      st_fumble_recoveries: 0,
    },
    discipline: {
      penalties: 5,
      penalty_yds: 45,
    },
  },
  
  // K - Chad Ryland
  {
    id: 'p7',
    name: 'Chad Ryland',
    team: 'NE',
    position: 'K',
    age: 24,
    availability: {
      games_played: 17,
      games_started: 0,
      snaps_off: 0,
      snaps_def: 0,
      snaps_st: 98,
    },
    kicking: {
      fg_made: 16,
      fg_att: 25,
      xp_made: 26,
      xp_att: 27,
      long_fg_made: 50,
    },
    kickoffs: {
      kickoffs: 67,
      touchbacks: 42,
      avg_kickoff_yds: 64.2,
      kickoff_returns_allowed: 25,
      kickoff_return_yds_allowed: 542,
    },
    discipline: {
      penalties: 0,
      penalty_yds: 0,
    },
  },
];

// Compute rate stats from raw stats
function computeRateStats(player: ComprehensivePlayerStats): RateStats {
  const rates: RateStats = {};
  const totalSnaps = player.availability.snaps_off + player.availability.snaps_def + player.availability.snaps_st;
  const gamesPlayed = player.availability.games_played || 1;
  
  // General rates
  if (totalSnaps > 0) {
    rates.snap_share_off = (player.availability.snaps_off / totalSnaps) * 100;
    rates.snap_share_def = (player.availability.snaps_def / totalSnaps) * 100;
    rates.snap_share_st = (player.availability.snaps_st / totalSnaps) * 100;
  }
  rates.games_active_pct = (gamesPlayed / 17) * 100;
  rates.starts_rate = (player.availability.games_started / gamesPlayed) * 100;
  
  // Passing rates
  if (player.passing) {
    const p = player.passing;
    rates.cmp_pct = (p.pass_cmp / p.pass_att) * 100;
    rates.yds_per_att = p.pass_yds / p.pass_att;
    rates.yds_per_cmp = p.pass_yds / p.pass_cmp;
    rates.td_pct = (p.pass_td / p.pass_att) * 100;
    rates.int_pct = (p.pass_int / p.pass_att) * 100;
    rates.sack_rate = (p.sacks_taken / (p.pass_att + p.sacks_taken)) * 100;
    rates.air_yds_share = (p.air_yds / p.pass_yds) * 100;
    rates.yac_share = (p.yac_gained / p.pass_yds) * 100;
    rates.deep_att_rate = (p.deep_att / p.pass_att) * 100;
    rates.play_action_rate = (p.play_action_att / p.pass_att) * 100;
    rates.screen_rate = (p.screen_att / p.pass_att) * 100;
    rates.pressure_rate = (p.pressure_dropbacks / p.pass_att) * 100;
    rates.hit_rate = (p.hits_on_qb / p.pass_att) * 100;
    rates.throwaway_rate = (p.throwaways / p.pass_att) * 100;
    rates.batted_rate = (p.batted_passes / p.pass_att) * 100;
    rates.drop_rate_against_qb = p.pass_att > 0 ? (p.drops_forced / p.pass_att) * 100 : 0;
    
    // NFL Passer Rating
    const a = ((p.pass_cmp / p.pass_att) - 0.3) * 5;
    const b = ((p.pass_yds / p.pass_att) - 3) * 0.25;
    const c = (p.pass_td / p.pass_att) * 20;
    const d = 2.375 - ((p.pass_int / p.pass_att) * 25);
    rates.passer_rating = ((Math.max(0, Math.min(a, 2.375)) + Math.max(0, Math.min(b, 2.375)) + Math.max(0, Math.min(c, 2.375)) + Math.max(0, Math.min(d, 2.375))) / 6) * 100;
  }
  
  // Rushing rates
  if (player.rushing) {
    const r = player.rushing;
    rates.yds_per_rush = r.rush_yds / r.rush_att;
    rates.td_rate_rush = (r.rush_td / r.rush_att) * 100;
    rates.yards_before_contact_per_att = r.yards_before_contact / r.rush_att;
    rates.yards_after_contact_per_att = r.yards_after_contact / r.rush_att;
    rates.designed_rush_share = (r.designed_rush_att / r.rush_att) * 100;
    rates.scramble_share = (r.scramble_att / r.rush_att) * 100;
  }
  
  // Receiving rates
  if (player.receiving) {
    const rec = player.receiving;
    rates.catch_pct = (rec.rec / rec.tar) * 100;
    rates.yds_per_rec = rec.rec_yds / rec.rec;
    rates.yds_per_target = rec.rec_yds / rec.tar;
    rates.td_per_target = (rec.rec_td / rec.tar) * 100;
    rates.air_yds_share_for = (rec.air_yds_for / rec.rec_yds) * 100;
    rates.yac_per_rec = rec.yac / rec.rec;
    rates.contested_catch_rate = (rec.contested_catches_won / rec.tar) * 100;
    rates.deep_target_rate = (rec.receptions_deep / rec.tar) * 100;
  }
  
  // Ball security rates
  if (player.ball_security) {
    const touches = (player.rushing?.rush_att || 0) + (player.receiving?.rec || 0);
    if (touches > 0) {
      rates.fumbles_per_touch = (player.ball_security.fumbles / touches) * 100;
      rates.lost_fumbles_per_touch = (player.ball_security.fumbles_lost / touches) * 100;
    }
  }
  
  // Defense rates
  if (player.defense_tackling) {
    const dt = player.defense_tackling;
    rates.tackles_per_game = dt.tackles / gamesPlayed;
    rates.missed_tackle_rate = (dt.missed_tackles / (dt.tackles + dt.missed_tackles)) * 100;
  }
  
  if (player.defense_pass_rush) {
    const dpr = player.defense_pass_rush;
    if (player.availability.snaps_def > 0) {
      rates.pressures_per_pass_snap = (dpr.pressures / player.availability.snaps_def) * 100;
    }
    if (dpr.pressures > 0) {
      rates.pressure_conversion_rate = (dpr.sacks / dpr.pressures) * 100;
    }
  }
  
  if (player.defense_coverage) {
    const dc = player.defense_coverage;
    rates.ints_per_game = dc.ints / gamesPlayed;
    rates.pbus_per_game = dc.pbus / gamesPlayed;
    rates.takeaways = dc.ints + dc.fr;
    if (dc.targets_defended > 0) {
      rates.comp_allowed_pct = (dc.receptions_allowed / dc.targets_defended) * 100;
    }
    if (dc.targets_defended > 0) {
      rates.yards_per_target_allowed = dc.rec_yds_allowed / dc.targets_defended;
    }
    if (dc.receptions_allowed > 0) {
      rates.yacs_allowed_per_rec = dc.yacs_allowed / dc.receptions_allowed;
    }
    if (player.availability.snaps_def > 0) {
      rates.penalty_rate_def = (dc.penalties_committed_def / player.availability.snaps_def) * 100;
    }
  }
  
  // Kicking rates
  if (player.kicking) {
    const k = player.kicking;
    rates.fg_pct = (k.fg_made / k.fg_att) * 100;
    rates.xp_pct = (k.xp_made / k.xp_att) * 100;
    rates.avg_fg_distance_made = k.long_fg_made;
  }
  
  // Punting rates
  if (player.punting) {
    const pn = player.punting;
    rates.gross_punt_avg = pn.punt_yds / pn.punts;
    rates.net_punt_avg = (pn.punt_yds - pn.punt_return_yds_allowed) / pn.punts;
    rates.inside_20_rate = (pn.punts_inside_20 / pn.punts) * 100;
    rates.punt_touchback_rate = (pn.punt_touchbacks / pn.punts) * 100;
  }
  
  // Kickoff rates
  if (player.kickoffs) {
    const ko = player.kickoffs;
    rates.touchback_rate = (ko.touchbacks / ko.kickoffs) * 100;
    rates.avg_kickoff_depth = ko.avg_kickoff_yds;
  }
  
  // Return rates
  if (player.returns) {
    const ret = player.returns;
    if (ret.kr > 0) rates.kr_avg = ret.kr_yds / ret.kr;
    if (ret.pr > 0) rates.pr_avg = ret.pr_yds / ret.pr;
    const totalReturns = ret.kr + ret.pr;
    const totalReturnTDs = ret.kr_td + ret.pr_td;
    if (totalReturns > 0) {
      rates.return_td_rate = (totalReturnTDs / totalReturns) * 100;
    }
    const stPlays = player.availability.snaps_st || 1;
    rates.st_tackle_rate = (ret.st_tackles / stPlays) * 100;
    if (ret.st_tackles + ret.st_missed_tackles > 0) {
      rates.st_missed_tackle_rate = (ret.st_missed_tackles / (ret.st_tackles + ret.st_missed_tackles)) * 100;
    }
  }
  
  return rates;
}

// Convert season stats to per game stats
function convertToPerGame(stats: ComprehensivePlayerStats): ComprehensivePlayerStats {
  const games = stats.availability.games_played || 1;
  const perGame = JSON.parse(JSON.stringify(stats)) as ComprehensivePlayerStats;
  
  // Helper to divide stats object
  const divideStats = (obj: any) => {
    for (const key in obj) {
      if (typeof obj[key] === 'number') {
        obj[key] = parseFloat((obj[key] / games).toFixed(2));
      }
    }
  };
  
  if (perGame.passing) divideStats(perGame.passing);
  if (perGame.rushing) divideStats(perGame.rushing);
  if (perGame.receiving) divideStats(perGame.receiving);
  if (perGame.ball_security) divideStats(perGame.ball_security);
  if (perGame.defense_tackling) divideStats(perGame.defense_tackling);
  if (perGame.defense_pass_rush) divideStats(perGame.defense_pass_rush);
  if (perGame.defense_coverage) divideStats(perGame.defense_coverage);
  if (perGame.kicking) divideStats(perGame.kicking);
  if (perGame.punting) divideStats(perGame.punting);
  if (perGame.kickoffs) divideStats(perGame.kickoffs);
  if (perGame.returns) divideStats(perGame.returns);
  divideStats(perGame.discipline);
  
  return perGame;
}

// Convert season stats to career stats (multiply by random years)
function convertToCareer(stats: ComprehensivePlayerStats): ComprehensivePlayerStats {
  const years = Math.floor(Math.random() * 5) + 3; // 3-7 seasons
  const career = JSON.parse(JSON.stringify(stats)) as ComprehensivePlayerStats;
  
  // Helper to multiply stats object
  const multiplyStats = (obj: any) => {
    for (const key in obj) {
      if (typeof obj[key] === 'number' && key !== 'long_punt' && key !== 'long_fg_made' && key !== 'avg_kickoff_yds') {
        obj[key] = Math.floor(obj[key] * years);
      }
    }
  };
  
  career.availability.games_played *= years;
  career.availability.games_started *= years;
  career.availability.snaps_off *= years;
  career.availability.snaps_def *= years;
  career.availability.snaps_st *= years;
  
  if (career.passing) multiplyStats(career.passing);
  if (career.rushing) multiplyStats(career.rushing);
  if (career.receiving) multiplyStats(career.receiving);
  if (career.ball_security) multiplyStats(career.ball_security);
  if (career.defense_tackling) multiplyStats(career.defense_tackling);
  if (career.defense_pass_rush) multiplyStats(career.defense_pass_rush);
  if (career.defense_coverage) multiplyStats(career.defense_coverage);
  if (career.kicking) multiplyStats(career.kicking);
  if (career.punting) multiplyStats(career.punting);
  if (career.kickoffs) multiplyStats(career.kickoffs);
  if (career.returns) multiplyStats(career.returns);
  multiplyStats(career.discipline);
  
  return career;
}

export const getAllStats = async (period: StatPeriod = 'season'): Promise<ComprehensivePlayerStats[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  
  if (period === 'per_game') {
    return SEASON_STATS.map(convertToPerGame);
  } else if (period === 'career') {
    return SEASON_STATS.map(convertToCareer);
  }
  return SEASON_STATS;
};

export const getPlayerRateStats = (player: ComprehensivePlayerStats): RateStats => {
  return computeRateStats(player);
};

export const getAvailablePositions = (): string[] => {
  return ['QB', 'RB', 'WR', 'TE', 'LB', 'CB', 'S', 'K', 'P'];
};

export const getAvailableTeams = (): string[] => {
  return Array.from(new Set(SEASON_STATS.map(p => p.team))).sort();
};
