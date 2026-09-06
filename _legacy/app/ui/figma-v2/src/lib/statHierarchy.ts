/**
 * Stat Hierarchy for Customize Stats Modal
 * Defines all available stats organized by category
 */

import { StatCategory } from '../components/stats/StatColumnChooser';

// PLAYER STATS HIERARCHY
export const playerStatCategories: StatCategory[] = [
  {
    id: 'core-identity',
    label: 'Core Identity & Participation',
    subcategories: [
      {
        id: 'identity',
        label: 'Identity',
        stats: [
          { id: 'player_name', variable: 'player_name', label: 'Player Name' },
          { id: 'player_num', variable: 'player_num', label: 'Jersey Number' },
          { id: 'player_pos', variable: 'player_pos', label: 'Position' },
          { id: 'player_team', variable: 'player_team', label: 'Team' },
          { id: 'player_age', variable: 'player_age', label: 'Age' },
          { id: 'player_exp', variable: 'player_exp', label: 'Years Experience' },
          { id: 'player_height', variable: 'player_height', label: 'Height' },
          { id: 'player_weight', variable: 'player_weight', label: 'Weight' },
        ],
      },
      {
        id: 'participation',
        label: 'Participation',
        stats: [
          { id: 'games_played', variable: 'games_played', label: 'Games Played', group: 'Base' },
          { id: 'games_started', variable: 'games_started', label: 'Games Started', group: 'Base' },
          { id: 'snaps_off', variable: 'snaps_off', label: 'Offensive Snaps', group: 'Base' },
          { id: 'snaps_def', variable: 'snaps_def', label: 'Defensive Snaps', group: 'Base' },
          { id: 'snaps_st', variable: 'snaps_st', label: 'Special Teams Snaps', group: 'Base' },
          { id: 'games_active_pct', variable: 'games_active_pct', label: 'Games Active %', group: 'Derived' },
          { id: 'starts_rate', variable: 'starts_rate', label: 'Start Rate %', group: 'Derived' },
          { id: 'snap_share_off', variable: 'snap_share_off', label: 'Offensive Snap Share %', group: 'Derived' },
          { id: 'snap_share_def', variable: 'snap_share_def', label: 'Defensive Snap Share %', group: 'Derived' },
          { id: 'snap_share_st', variable: 'snap_share_st', label: 'Special Teams Snap Share %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'qb-passing',
    label: 'QB — Passing',
    subcategories: [
      {
        id: 'qb-pass-base',
        label: 'Base Passing',
        stats: [
          { id: 'pass_att', variable: 'pass_att', label: 'Pass Attempts', group: 'Base' },
          { id: 'pass_cmp', variable: 'pass_cmp', label: 'Completions', group: 'Base' },
          { id: 'pass_yds', variable: 'pass_yds', label: 'Passing Yards', group: 'Base' },
          { id: 'pass_td', variable: 'pass_td', label: 'Passing TDs', group: 'Base' },
          { id: 'pass_int', variable: 'pass_int', label: 'Interceptions', group: 'Base' },
          { id: 'qb_cmp_pct', variable: 'qb_cmp_pct', label: 'Completion Percentage', group: 'Derived' },
          { id: 'qb_yds_per_att', variable: 'qb_yds_per_att', label: 'Yards per Attempt', group: 'Derived' },
          { id: 'qb_yds_per_cmp', variable: 'qb_yds_per_cmp', label: 'Yards per Completion', group: 'Derived' },
          { id: 'qb_td_pct', variable: 'qb_td_pct', label: 'TD %', group: 'Derived' },
          { id: 'qb_int_pct', variable: 'qb_int_pct', label: 'INT %', group: 'Derived' },
          { id: 'qb_rating', variable: 'qb_rating', label: 'Passer Rating', group: 'Derived' },
        ],
      },
      {
        id: 'qb-pass-advanced',
        label: 'Advanced Passing',
        stats: [
          { id: 'air_yds', variable: 'air_yds', label: 'Air Yards', group: 'Base' },
          { id: 'yac_gained', variable: 'yac_gained', label: 'YAC Gained', group: 'Base' },
          { id: 'throwaways', variable: 'throwaways', label: 'Throwaways', group: 'Base' },
          { id: 'spikes', variable: 'spikes', label: 'Spikes', group: 'Base' },
          { id: 'batted_passes', variable: 'batted_passes', label: 'Batted Passes', group: 'Base' },
          { id: 'drops_forced', variable: 'drops_forced', label: 'Receiver Drops', group: 'Base' },
          { id: 'air_yds_per_att', variable: 'air_yds_per_att', label: 'Air Yards per Attempt', group: 'Derived' },
          { id: 'air_yds_share', variable: 'air_yds_share', label: 'Air Yards Share %', group: 'Derived' },
          { id: 'yac_share', variable: 'yac_share', label: 'YAC Share %', group: 'Derived' },
          { id: 'throwaway_rate', variable: 'throwaway_rate', label: 'Throwaway Rate %', group: 'Derived' },
          { id: 'drop_rate', variable: 'drop_rate', label: 'Drop Rate %', group: 'Derived' },
        ],
      },
      {
        id: 'qb-pass-situation',
        label: 'Situational Passing',
        stats: [
          { id: 'play_action_att', variable: 'play_action_att', label: 'Play Action Attempts', group: 'Base' },
          { id: 'screen_att', variable: 'screen_att', label: 'Screen Attempts', group: 'Base' },
          { id: 'deep_att', variable: 'deep_att', label: 'Deep Attempts (20+ yds)', group: 'Base' },
          { id: 'play_action_rate', variable: 'play_action_rate', label: 'Play Action Rate %', group: 'Derived' },
          { id: 'screen_rate', variable: 'screen_rate', label: 'Screen Rate %', group: 'Derived' },
          { id: 'deep_att_rate', variable: 'deep_att_rate', label: 'Deep Attempt Rate %', group: 'Derived' },
        ],
      },
      {
        id: 'qb-pass-pressure',
        label: 'Under Pressure',
        stats: [
          { id: 'sacks_taken', variable: 'sacks_taken', label: 'Sacks Taken', group: 'Base' },
          { id: 'pressure_dropbacks', variable: 'pressure_dropbacks', label: 'Pressured Dropbacks', group: 'Base' },
          { id: 'hits_on_qb', variable: 'hits_on_qb', label: 'QB Hits Taken', group: 'Base' },
          { id: 'sack_rate', variable: 'sack_rate', label: 'Sack Rate %', group: 'Derived' },
          { id: 'pressure_rate', variable: 'pressure_rate', label: 'Pressure Rate %', group: 'Derived' },
          { id: 'hit_rate', variable: 'hit_rate', label: 'Hit Rate %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'qb-rushing',
    label: 'QB — Rushing/Scramble',
    subcategories: [
      {
        id: 'qb-rush',
        label: 'QB Rushing',
        stats: [
          { id: 'qb_rush_att', variable: 'qb_rush_att', label: 'Rushing Attempts', group: 'Base' },
          { id: 'qb_rush_yds', variable: 'qb_rush_yds', label: 'Rushing Yards', group: 'Base' },
          { id: 'qb_rush_td', variable: 'qb_rush_td', label: 'Rushing TDs', group: 'Base' },
          { id: 'designed_rush_att', variable: 'designed_rush_att', label: 'Designed Rushes', group: 'Base' },
          { id: 'scramble_att', variable: 'scramble_att', label: 'Scrambles', group: 'Base' },
          { id: 'qb_yds_per_rush', variable: 'qb_yds_per_rush', label: 'Yards per Rush', group: 'Derived' },
          { id: 'designed_rush_share', variable: 'designed_rush_share', label: 'Designed Rush %', group: 'Derived' },
          { id: 'scramble_share', variable: 'scramble_share', label: 'Scramble %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'rb-rushing',
    label: 'RB — Rushing',
    subcategories: [
      {
        id: 'rb-rush-base',
        label: 'Base Rushing',
        stats: [
          { id: 'rb_rush_att', variable: 'rb_rush_att', label: 'Rushing Attempts', group: 'Base' },
          { id: 'rb_rush_yds', variable: 'rb_rush_yds', label: 'Rushing Yards', group: 'Base' },
          { id: 'rb_rush_td', variable: 'rb_rush_td', label: 'Rushing TDs', group: 'Base' },
          { id: 'rb_yds_per_rush', variable: 'rb_yds_per_rush', label: 'Yards per Rush', group: 'Derived' },
          { id: 'rb_td_rate_rush', variable: 'rb_td_rate_rush', label: 'TD Rate %', group: 'Derived' },
        ],
      },
      {
        id: 'rb-rush-advanced',
        label: 'Advanced Rushing',
        stats: [
          { id: 'yards_before_contact', variable: 'yards_before_contact', label: 'Yards Before Contact', group: 'Base' },
          { id: 'yards_after_contact', variable: 'yards_after_contact', label: 'Yards After Contact', group: 'Base' },
          { id: 'broken_tackles', variable: 'broken_tackles', label: 'Broken Tackles', group: 'Base' },
          { id: 'stuffed_runs', variable: 'stuffed_runs', label: 'Stuffed Runs (≤0 yds)', group: 'Base' },
          { id: 'ybc_per_att', variable: 'ybc_per_att', label: 'YBC per Attempt', group: 'Derived' },
          { id: 'yac_per_att', variable: 'yac_per_att', label: 'YAC per Attempt', group: 'Derived' },
          { id: 'broken_tackle_rate', variable: 'broken_tackle_rate', label: 'Broken Tackle Rate %', group: 'Derived' },
          { id: 'stuff_rate', variable: 'stuff_rate', label: 'Stuff Rate %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'receiving',
    label: 'Receiving (All)',
    subcategories: [
      {
        id: 'rec-base',
        label: 'Base Receiving',
        stats: [
          { id: 'targets', variable: 'targets', label: 'Targets', group: 'Base' },
          { id: 'receptions', variable: 'receptions', label: 'Receptions', group: 'Base' },
          { id: 'rec_yds', variable: 'rec_yds', label: 'Receiving Yards', group: 'Base' },
          { id: 'rec_td', variable: 'rec_td', label: 'Receiving TDs', group: 'Base' },
          { id: 'catch_pct', variable: 'catch_pct', label: 'Catch %', group: 'Derived' },
          { id: 'yds_per_rec', variable: 'yds_per_rec', label: 'Yards per Reception', group: 'Derived' },
          { id: 'yds_per_target', variable: 'yds_per_target', label: 'Yards per Target', group: 'Derived' },
          { id: 'rec_td_rate', variable: 'rec_td_rate', label: 'TD Rate %', group: 'Derived' },
        ],
      },
      {
        id: 'rec-advanced',
        label: 'Advanced Receiving',
        stats: [
          { id: 'rec_air_yds', variable: 'rec_air_yds', label: 'Air Yards', group: 'Base' },
          { id: 'rec_yac', variable: 'rec_yac', label: 'Yards After Catch', group: 'Base' },
          { id: 'drops', variable: 'drops', label: 'Drops', group: 'Base' },
          { id: 'contested_catches', variable: 'contested_catches', label: 'Contested Catches', group: 'Base' },
          { id: 'first_downs_rec', variable: 'first_downs_rec', label: 'First Downs', group: 'Base' },
          { id: 'rec_yac_per_rec', variable: 'rec_yac_per_rec', label: 'YAC per Reception', group: 'Derived' },
          { id: 'drop_rate_rec', variable: 'drop_rate_rec', label: 'Drop Rate %', group: 'Derived' },
          { id: 'contested_catch_rate', variable: 'contested_catch_rate', label: 'Contested Catch Rate %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'defense-tackling',
    label: 'Defense — Tackling',
    subcategories: [
      {
        id: 'def-tackle-base',
        label: 'Base Tackling',
        stats: [
          { id: 'tackles_solo', variable: 'tackles_solo', label: 'Solo Tackles', group: 'Base' },
          { id: 'tackles_assist', variable: 'tackles_assist', label: 'Assisted Tackles', group: 'Base' },
          { id: 'tackles_combined', variable: 'tackles_combined', label: 'Combined Tackles', group: 'Base' },
          { id: 'tackles_for_loss', variable: 'tackles_for_loss', label: 'Tackles for Loss', group: 'Base' },
          { id: 'missed_tackles', variable: 'missed_tackles', label: 'Missed Tackles', group: 'Base' },
          { id: 'tackles_per_game', variable: 'tackles_per_game', label: 'Tackles per Game', group: 'Derived' },
          { id: 'tackle_efficiency', variable: 'tackle_efficiency', label: 'Tackle Efficiency %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'defense-pass-rush',
    label: 'Defense — Pass Rush (DL/LB)',
    subcategories: [
      {
        id: 'def-pass-rush',
        label: 'Pass Rush',
        stats: [
          { id: 'sacks', variable: 'sacks', label: 'Sacks', group: 'Base' },
          { id: 'qb_hits', variable: 'qb_hits', label: 'QB Hits', group: 'Base' },
          { id: 'qb_hurries', variable: 'qb_hurries', label: 'QB Hurries', group: 'Base' },
          { id: 'pressures', variable: 'pressures', label: 'Pressures', group: 'Base' },
          { id: 'pass_rush_snaps', variable: 'pass_rush_snaps', label: 'Pass Rush Snaps', group: 'Base' },
          { id: 'sack_rate_def', variable: 'sack_rate_def', label: 'Sack Rate %', group: 'Derived' },
          { id: 'pressure_rate_def', variable: 'pressure_rate_def', label: 'Pressure Rate %', group: 'Derived' },
          { id: 'win_rate', variable: 'win_rate', label: 'Win Rate %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'defense-coverage',
    label: 'Defense — Coverage (DB/LB)',
    subcategories: [
      {
        id: 'def-coverage',
        label: 'Coverage',
        stats: [
          { id: 'targets_allowed', variable: 'targets_allowed', label: 'Targets Allowed', group: 'Base' },
          { id: 'receptions_allowed', variable: 'receptions_allowed', label: 'Receptions Allowed', group: 'Base' },
          { id: 'yds_allowed', variable: 'yds_allowed', label: 'Yards Allowed', group: 'Base' },
          { id: 'tds_allowed', variable: 'tds_allowed', label: 'TDs Allowed', group: 'Base' },
          { id: 'pass_breakups', variable: 'pass_breakups', label: 'Pass Breakups', group: 'Base' },
          { id: 'interceptions', variable: 'interceptions', label: 'Interceptions', group: 'Base' },
          { id: 'cov_catch_pct_allowed', variable: 'cov_catch_pct_allowed', label: 'Catch % Allowed', group: 'Derived' },
          { id: 'yds_per_target_allowed', variable: 'yds_per_target_allowed', label: 'Yards per Target Allowed', group: 'Derived' },
          { id: 'passer_rating_allowed', variable: 'passer_rating_allowed', label: 'Passer Rating Allowed', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'turnovers',
    label: 'Turnovers & Ball Security',
    subcategories: [
      {
        id: 'turnovers-off',
        label: 'Offensive Turnovers',
        stats: [
          { id: 'fumbles', variable: 'fumbles', label: 'Fumbles', group: 'Base' },
          { id: 'fumbles_lost', variable: 'fumbles_lost', label: 'Fumbles Lost', group: 'Base' },
          { id: 'fumbles_per_touch', variable: 'fumbles_per_touch', label: 'Fumbles per Touch', group: 'Derived' },
          { id: 'fumbles_lost_per_touch', variable: 'fumbles_lost_per_touch', label: 'Fumbles Lost per Touch', group: 'Derived' },
        ],
      },
      {
        id: 'turnovers-def',
        label: 'Defensive Turnovers',
        stats: [
          { id: 'int_def', variable: 'int_def', label: 'Interceptions', group: 'Base' },
          { id: 'fumbles_forced', variable: 'fumbles_forced', label: 'Fumbles Forced', group: 'Base' },
          { id: 'fumbles_recovered', variable: 'fumbles_recovered', label: 'Fumbles Recovered', group: 'Base' },
          { id: 'defensive_tds', variable: 'defensive_tds', label: 'Defensive TDs', group: 'Base' },
        ],
      },
    ],
  },
  {
    id: 'kicking',
    label: 'Kicking',
    subcategories: [
      {
        id: 'field-goals',
        label: 'Field Goals',
        stats: [
          { id: 'fg_att', variable: 'fg_att', label: 'FG Attempts', group: 'Base' },
          { id: 'fg_made', variable: 'fg_made', label: 'FG Made', group: 'Base' },
          { id: 'fg_pct', variable: 'fg_pct', label: 'FG %', group: 'Derived' },
          { id: 'fg_long', variable: 'fg_long', label: 'Longest FG', group: 'Base' },
          { id: 'fg_0_19', variable: 'fg_0_19', label: 'FG 0-19 yds', group: 'Base' },
          { id: 'fg_20_29', variable: 'fg_20_29', label: 'FG 20-29 yds', group: 'Base' },
          { id: 'fg_30_39', variable: 'fg_30_39', label: 'FG 30-39 yds', group: 'Base' },
          { id: 'fg_40_49', variable: 'fg_40_49', label: 'FG 40-49 yds', group: 'Base' },
          { id: 'fg_50_plus', variable: 'fg_50_plus', label: 'FG 50+ yds', group: 'Base' },
        ],
      },
      {
        id: 'extra-points',
        label: 'Extra Points',
        stats: [
          { id: 'xp_att', variable: 'xp_att', label: 'XP Attempts', group: 'Base' },
          { id: 'xp_made', variable: 'xp_made', label: 'XP Made', group: 'Base' },
          { id: 'xp_pct', variable: 'xp_pct', label: 'XP %', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'punting',
    label: 'Punting',
    subcategories: [
      {
        id: 'punt-base',
        label: 'Punting',
        stats: [
          { id: 'punts', variable: 'punts', label: 'Punts', group: 'Base' },
          { id: 'punt_yds', variable: 'punt_yds', label: 'Punt Yards', group: 'Base' },
          { id: 'punt_avg', variable: 'punt_avg', label: 'Punt Average', group: 'Derived' },
          { id: 'punt_long', variable: 'punt_long', label: 'Longest Punt', group: 'Base' },
          { id: 'punts_inside_20', variable: 'punts_inside_20', label: 'Punts Inside 20', group: 'Base' },
          { id: 'touchbacks', variable: 'touchbacks', label: 'Touchbacks', group: 'Base' },
          { id: 'fair_catches', variable: 'fair_catches', label: 'Fair Catches', group: 'Base' },
        ],
      },
    ],
  },
  {
    id: 'kick-return',
    label: 'Kick Returning',
    subcategories: [
      {
        id: 'kick-ret',
        label: 'Kick Returns',
        stats: [
          { id: 'kick_returns', variable: 'kick_returns', label: 'Kick Returns', group: 'Base' },
          { id: 'kick_return_yds', variable: 'kick_return_yds', label: 'Kick Return Yards', group: 'Base' },
          { id: 'kick_return_td', variable: 'kick_return_td', label: 'Kick Return TDs', group: 'Base' },
          { id: 'kick_return_avg', variable: 'kick_return_avg', label: 'Kick Return Average', group: 'Derived' },
          { id: 'kick_return_long', variable: 'kick_return_long', label: 'Longest Kick Return', group: 'Base' },
        ],
      },
      {
        id: 'punt-ret',
        label: 'Punt Returns',
        stats: [
          { id: 'punt_returns', variable: 'punt_returns', label: 'Punt Returns', group: 'Base' },
          { id: 'punt_return_yds', variable: 'punt_return_yds', label: 'Punt Return Yards', group: 'Base' },
          { id: 'punt_return_td', variable: 'punt_return_td', label: 'Punt Return TDs', group: 'Base' },
          { id: 'punt_return_avg', variable: 'punt_return_avg', label: 'Punt Return Average', group: 'Derived' },
          { id: 'punt_return_long', variable: 'punt_return_long', label: 'Longest Punt Return', group: 'Base' },
        ],
      },
    ],
  },
];

// TEAM STATS HIERARCHY
export const teamStatCategories: StatCategory[] = [
  {
    id: 'team-identity',
    label: 'Identity & Record',
    subcategories: [
      {
        id: 'team-id',
        label: 'Team Identity',
        stats: [
          { id: 'team_name', variable: 'team_name', label: 'Team Name' },
          { id: 'team_abbr', variable: 'team_abbr', label: 'Team Abbreviation' },
          { id: 'conference', variable: 'conference', label: 'Conference' },
          { id: 'division', variable: 'division', label: 'Division' },
        ],
      },
      {
        id: 'team-record',
        label: 'Record',
        stats: [
          { id: 'wins', variable: 'wins', label: 'Wins', group: 'Base' },
          { id: 'losses', variable: 'losses', label: 'Losses', group: 'Base' },
          { id: 'ties', variable: 'ties', label: 'Ties', group: 'Base' },
          { id: 'win_pct', variable: 'win_pct', label: 'Win %', group: 'Derived' },
          { id: 'points_for', variable: 'points_for', label: 'Points For', group: 'Base' },
          { id: 'points_against', variable: 'points_against', label: 'Points Against', group: 'Base' },
          { id: 'point_diff', variable: 'point_diff', label: 'Point Differential', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'team-offense',
    label: 'Team Offense',
    subcategories: [
      {
        id: 'team-off-total',
        label: 'Total Offense',
        stats: [
          { id: 'off_plays', variable: 'off_plays', label: 'Offensive Plays', group: 'Base' },
          { id: 'off_yds', variable: 'off_yds', label: 'Total Yards', group: 'Base' },
          { id: 'off_yds_per_play', variable: 'off_yds_per_play', label: 'Yards per Play', group: 'Derived' },
          { id: 'off_first_downs', variable: 'off_first_downs', label: 'First Downs', group: 'Base' },
          { id: 'off_third_down_conv', variable: 'off_third_down_conv', label: '3rd Down Conversions', group: 'Base' },
          { id: 'off_third_down_pct', variable: 'off_third_down_pct', label: '3rd Down %', group: 'Derived' },
          { id: 'off_turnovers', variable: 'off_turnovers', label: 'Turnovers', group: 'Base' },
        ],
      },
      {
        id: 'team-off-pass',
        label: 'Passing Offense',
        stats: [
          { id: 'team_pass_att', variable: 'team_pass_att', label: 'Pass Attempts', group: 'Base' },
          { id: 'team_pass_cmp', variable: 'team_pass_cmp', label: 'Completions', group: 'Base' },
          { id: 'team_pass_yds', variable: 'team_pass_yds', label: 'Passing Yards', group: 'Base' },
          { id: 'team_pass_td', variable: 'team_pass_td', label: 'Passing TDs', group: 'Base' },
          { id: 'team_pass_int', variable: 'team_pass_int', label: 'Interceptions Thrown', group: 'Base' },
          { id: 'team_sacks_allowed', variable: 'team_sacks_allowed', label: 'Sacks Allowed', group: 'Base' },
          { id: 'team_cmp_pct', variable: 'team_cmp_pct', label: 'Completion %', group: 'Derived' },
          { id: 'team_pass_yds_per_att', variable: 'team_pass_yds_per_att', label: 'Yards per Attempt', group: 'Derived' },
        ],
      },
      {
        id: 'team-off-rush',
        label: 'Rushing Offense',
        stats: [
          { id: 'team_rush_att', variable: 'team_rush_att', label: 'Rush Attempts', group: 'Base' },
          { id: 'team_rush_yds', variable: 'team_rush_yds', label: 'Rushing Yards', group: 'Base' },
          { id: 'team_rush_td', variable: 'team_rush_td', label: 'Rushing TDs', group: 'Base' },
          { id: 'team_rush_yds_per_att', variable: 'team_rush_yds_per_att', label: 'Yards per Rush', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'team-defense',
    label: 'Team Defense',
    subcategories: [
      {
        id: 'team-def-total',
        label: 'Total Defense',
        stats: [
          { id: 'def_plays', variable: 'def_plays', label: 'Defensive Plays', group: 'Base' },
          { id: 'def_yds_allowed', variable: 'def_yds_allowed', label: 'Total Yards Allowed', group: 'Base' },
          { id: 'def_yds_per_play', variable: 'def_yds_per_play', label: 'Yards per Play Allowed', group: 'Derived' },
          { id: 'def_points_allowed', variable: 'def_points_allowed', label: 'Points Allowed', group: 'Base' },
          { id: 'def_turnovers_forced', variable: 'def_turnovers_forced', label: 'Turnovers Forced', group: 'Base' },
        ],
      },
      {
        id: 'team-def-pass',
        label: 'Pass Defense',
        stats: [
          { id: 'team_pass_att_allowed', variable: 'team_pass_att_allowed', label: 'Pass Attempts Allowed', group: 'Base' },
          { id: 'team_pass_cmp_allowed', variable: 'team_pass_cmp_allowed', label: 'Completions Allowed', group: 'Base' },
          { id: 'team_pass_yds_allowed', variable: 'team_pass_yds_allowed', label: 'Passing Yards Allowed', group: 'Base' },
          { id: 'team_pass_td_allowed', variable: 'team_pass_td_allowed', label: 'Passing TDs Allowed', group: 'Base' },
          { id: 'team_int_def', variable: 'team_int_def', label: 'Interceptions', group: 'Base' },
          { id: 'team_sacks', variable: 'team_sacks', label: 'Sacks', group: 'Base' },
        ],
      },
      {
        id: 'team-def-rush',
        label: 'Rush Defense',
        stats: [
          { id: 'team_rush_att_allowed', variable: 'team_rush_att_allowed', label: 'Rush Attempts Allowed', group: 'Base' },
          { id: 'team_rush_yds_allowed', variable: 'team_rush_yds_allowed', label: 'Rushing Yards Allowed', group: 'Base' },
          { id: 'team_rush_td_allowed', variable: 'team_rush_td_allowed', label: 'Rushing TDs Allowed', group: 'Base' },
          { id: 'team_rush_yds_per_att_allowed', variable: 'team_rush_yds_per_att_allowed', label: 'Yards per Rush Allowed', group: 'Derived' },
        ],
      },
    ],
  },
  {
    id: 'team-special',
    label: 'Special Teams',
    subcategories: [
      {
        id: 'team-st',
        label: 'Special Teams',
        stats: [
          { id: 'team_fg_pct', variable: 'team_fg_pct', label: 'FG %', group: 'Derived' },
          { id: 'team_punt_avg', variable: 'team_punt_avg', label: 'Punt Average', group: 'Derived' },
          { id: 'team_kick_return_avg', variable: 'team_kick_return_avg', label: 'Kick Return Avg', group: 'Derived' },
          { id: 'team_punt_return_avg', variable: 'team_punt_return_avg', label: 'Punt Return Avg', group: 'Derived' },
        ],
      },
    ],
  },
];

// COACH STATS HIERARCHY
export const coachStatCategories: StatCategory[] = [
  {
    id: 'coach-identity',
    label: 'Coach Identity',
    subcategories: [
      {
        id: 'coach-id',
        label: 'Identity',
        stats: [
          { id: 'coach_name', variable: 'coach_name', label: 'Coach Name' },
          { id: 'coach_role', variable: 'coach_role', label: 'Role (HC/OC/DC)' },
          { id: 'coach_team', variable: 'coach_team', label: 'Team' },
          { id: 'coach_age', variable: 'coach_age', label: 'Age' },
          { id: 'coach_exp', variable: 'coach_exp', label: 'Years Experience' },
        ],
      },
    ],
  },
  {
    id: 'coach-record',
    label: 'Coaching Record (HC only)',
    subcategories: [
      {
        id: 'coach-rec',
        label: 'Record',
        stats: [
          { id: 'hc_wins', variable: 'hc_wins', label: 'Wins', group: 'Base' },
          { id: 'hc_losses', variable: 'hc_losses', label: 'Losses', group: 'Base' },
          { id: 'hc_ties', variable: 'hc_ties', label: 'Ties', group: 'Base' },
          { id: 'hc_win_pct', variable: 'hc_win_pct', label: 'Win %', group: 'Derived' },
          { id: 'playoff_app', variable: 'playoff_app', label: 'Playoff Appearances', group: 'Base' },
          { id: 'playoff_wins', variable: 'playoff_wins', label: 'Playoff Wins', group: 'Base' },
          { id: 'super_bowls', variable: 'super_bowls', label: 'Super Bowl Wins', group: 'Base' },
        ],
      },
    ],
  },
  {
    id: 'coach-performance',
    label: 'Performance Metrics',
    subcategories: [
      {
        id: 'coach-perf',
        label: 'Performance',
        stats: [
          { id: 'avg_points_scored', variable: 'avg_points_scored', label: 'Avg Points Scored', group: 'Derived' },
          { id: 'avg_points_allowed', variable: 'avg_points_allowed', label: 'Avg Points Allowed', group: 'Derived' },
          { id: 'turnover_diff', variable: 'turnover_diff', label: 'Turnover Differential', group: 'Derived' },
          { id: 'avg_yards_per_game', variable: 'avg_yards_per_game', label: 'Avg Yards per Game', group: 'Derived' },
        ],
      },
    ],
  },
];
