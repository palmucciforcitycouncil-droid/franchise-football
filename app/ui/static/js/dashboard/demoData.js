// Demo JSON for all 5 dashboard widgets; used on API failure/empty responses.
export const demoStandings = {
  division: "AFC East",
  rows: [
    { team_id: "BUF", w: 10, l: 7, t: 0, pct: 0.588, pf: 421, pa: 342, home: "6-2", away: "4-5", strk: "W2" },
    { team_id: "MIA", w: 9,  l: 8, t: 0, pct: 0.529, pf: 398, pa: 359, home: "5-3", away: "4-5", strk: "L1" },
    { team_id: "NE",  w: 8,  l: 9, t: 0, pct: 0.471, pf: 364, pa: 371, home: "3-5", away: "5-4", strk: "W1" },
    { team_id: "NYJ", w: 4,  l: 13,t: 0, pct: 0.235, pf: 287, pa: 426, home: "2-6", away: "2-7", strk: "L3" }
  ]
};

export const demoPowerRankings = {
  as_of: "2025-10-15",
  rows: Array.from({length:32}, (_,i)=>({
    rank: i+1,
    team_id: ["SF","KC","BAL","BUF","PHI","DET","DAL","MIA","CIN","NE","NYJ","LAR","PIT","GB","SEA","HOU","JAX","CLE","MIN","NO","TB","ATL","IND","LAC","CHI","TEN","LV","NYG","ARI","WAS","DEN","CAR"][i],
    power: 1692 - i*9,
    delta: ([" +2"," -1"," +1"," -2"," 0"," -1"," +1"," -3"," 0"," +2"," -2"," +1"," 0"," -1"," 0"," +1"," 0"," -2"," +1"," 0"," -1"," 0"," +1"," -1"," 0"," -1"," 0"," +1"," -1"," 0"," +1"," -1"][i]||" 0").trim()
  }))
};

export const demoSchedule = {
  team_id: "NE",
  season: 2025,
  games: [
    { week:1, home:true,  opp_id:"BUF", team_pts:24, opp_pts:21, result:"W", record_after:"1-0" },
    { week:2, home:false, opp_id:"MIA", team_pts:17, opp_pts:28, result:"L", record_after:"1-1" },
    { week:3, home:true,  opp_id:"NYJ", team_pts:31, opp_pts:14, result:"W", record_after:"2-1" },
    { week:4, home:false, opp_id:"BAL", team_pts:20, opp_pts:27, result:"L", record_after:"2-2" },
    { week:5, home:true,  opp_id:"CIN", team_pts:35, opp_pts:21, result:"W", record_after:"3-2" }
  ]
};

export const demoScout = {
  team_id:"BUF", record:"10-7", streak:"W2",
  last3:["W 24-17","W 20-10","L 21-27"],
  leaders:{ QB:"J. Allen (89)", RB:"J. Cook (84)", WR1:"S. Diggs (92)" },
  injuries:[ {player:"TE2",status:"Q",note:"ankle"}, {player:"CB1",status:"D",note:"hamstring"} ],
  tendencies:{ run:42, pass:58, pace:62, aggression:55, blitz:31, man:48, zone:52 }
};

export const demoBox = {
  game_id:"2025-W01-NE-BUF",
  home_id:"BUF", away_id:"NE",
  quarters:[ {NE:7,BUF:3}, {NE:10,BUF:7}, {NE:7,BUF:0}, {NE:3,BUF:7} ],
  totals:{ NE:27, BUF:17 }
};