import { ColDef } from './columnsAttributes';

export const statsColumns: ColDef[] = [
  // CORE group
  {
    key: "name",
    label: "Name",
    width: 180,
    minWidth: 140,
    maxWidth: 220,
    align: "left",
    tooltip: "Player name and position",
    group: "CORE",
    fixed: true
  },
  {
    key: "gp",
    label: "GP",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Games Played",
    group: "CORE",
    numeric: true
  },
  {
    key: "gs",
    label: "GS",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Games Started",
    group: "CORE",
    numeric: true
  },

  // QB group
  {
    key: "cmp",
    label: "CMP",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Completions",
    group: "QB",
    numeric: true
  },
  {
    key: "att",
    label: "ATT",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Attempts",
    group: "QB",
    numeric: true
  },
  {
    key: "cmp_pct",
    label: "CMP%",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Completion Percentage",
    group: "QB",
    numeric: true
  },
  {
    key: "yds",
    label: "YDS",
    width: 70,
    minWidth: 60,
    maxWidth: 80,
    align: "center",
    tooltip: "Passing Yards",
    group: "QB",
    numeric: true
  },
  {
    key: "td",
    label: "TD",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Touchdowns",
    group: "QB",
    numeric: true
  },
  {
    key: "int",
    label: "INT",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Interceptions",
    group: "QB",
    numeric: true
  },
  {
    key: "rtg",
    label: "RTG",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Passer Rating",
    group: "QB",
    numeric: true
  },

  // RB group
  {
    key: "rush_att",
    label: "RUSH",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Rush Attempts",
    group: "RB",
    numeric: true
  },
  {
    key: "rush_yds",
    label: "RYDS",
    width: 70,
    minWidth: 60,
    maxWidth: 80,
    align: "center",
    tooltip: "Rush Yards",
    group: "RB",
    numeric: true
  },
  {
    key: "rush_avg",
    label: "RAVG",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Rush Average",
    group: "RB",
    numeric: true
  },
  {
    key: "rush_td",
    label: "RTD",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Rush Touchdowns",
    group: "RB",
    numeric: true
  },

  // REC group
  {
    key: "rec",
    label: "REC",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Receptions",
    group: "REC",
    numeric: true
  },
  {
    key: "rec_yds",
    label: "RYDS",
    width: 70,
    minWidth: 60,
    maxWidth: 80,
    align: "center",
    tooltip: "Receiving Yards",
    group: "REC",
    numeric: true
  },
  {
    key: "rec_avg",
    label: "RAVG",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Receiving Average",
    group: "REC",
    numeric: true
  },
  {
    key: "rec_td",
    label: "RTD",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Receiving Touchdowns",
    group: "REC",
    numeric: true
  },

  // DEF group
  {
    key: "tackles",
    label: "TACK",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Tackles",
    group: "DEF",
    numeric: true
  },
  {
    key: "sacks",
    label: "SACK",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Sacks",
    group: "DEF",
    numeric: true
  },
  {
    key: "int_def",
    label: "INT",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Interceptions",
    group: "DEF",
    numeric: true
  },
  {
    key: "ff",
    label: "FF",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Forced Fumbles",
    group: "DEF",
    numeric: true
  },
  {
    key: "fr",
    label: "FR",
    width: 50,
    minWidth: 40,
    maxWidth: 60,
    align: "center",
    tooltip: "Fumble Recoveries",
    group: "DEF",
    numeric: true
  },

  // ST group
  {
    key: "fg_made",
    label: "FGM",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Field Goals Made",
    group: "ST",
    numeric: true
  },
  {
    key: "fg_att",
    label: "FGA",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Field Goals Attempted",
    group: "ST",
    numeric: true
  },
  {
    key: "fg_pct",
    label: "FG%",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Field Goal Percentage",
    group: "ST",
    numeric: true
  },
  {
    key: "xp_made",
    label: "XPM",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Extra Points Made",
    group: "ST",
    numeric: true
  },
  {
    key: "punt_avg",
    label: "PAVG",
    width: 70,
    minWidth: 60,
    maxWidth: 80,
    align: "center",
    tooltip: "Punt Average",
    group: "ST",
    numeric: true
  }
];
