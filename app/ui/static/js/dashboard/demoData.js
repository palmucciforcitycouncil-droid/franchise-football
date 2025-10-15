// Centralized demo data for dashboard widgets
// Used when API calls fail or return empty

export const demoSchedule = [
  {week:1, home:true, opp:"BUF", team_id:"NE", score_team:24, score_opp:21, result:"W", record:"8-9"},
  {week:2, home:false, opp:"MIA", team_id:"NE", score_team:17, score_opp:28, result:"L", record:"8-9"},
  {week:3, home:true, opp:"NYJ", team_id:"NE", score_team:31, score_opp:14, result:"W", record:"8-9"},
  {week:4, home:false, opp:"BAL", team_id:"NE", score_team:20, score_opp:27, result:"L", record:"8-9"},
  {week:5, home:true, opp:"CIN", team_id:"NE", score_team:35, score_opp:21, result:"W", record:"8-9"},
  {week:6, home:false, opp:"LV", team_id:"NE", score_team:24, score_opp:17, result:"W", record:"8-9"},
  {week:7, home:true, opp:"DEN", team_id:"NE", score_team:28, score_opp:14, result:"W", record:"8-9"},
  {week:8, home:false, opp:"LAC", team_id:"NE", score_team:21, score_opp:31, result:"L", record:"8-9"},
  {week:9, home:true, opp:"KC", team_id:"NE", score_team:17, score_opp:24, result:"L", record:"8-9"},
  {week:10, home:false, opp:"TEN", team_id:"NE", score_team:27, score_opp:20, result:"W", record:"8-9"},
  {week:11, home:true, opp:"HOU", team_id:"NE", score_team:31, score_opp:28, result:"W", record:"8-9"},
  {week:12, home:false, opp:"IND", team_id:"NE", score_team:24, score_opp:21, result:"W", record:"8-9"},
  {week:13, home:true, opp:"JAX", team_id:"NE", score_team:28, score_opp:17, result:"W", record:"8-9"},
  {week:14, home:false, opp:"PIT", team_id:"NE", score_team:21, score_opp:24, result:"L", record:"8-9"},
  {week:15, home:true, opp:"CLE", team_id:"NE", score_team:27, score_opp:20, result:"W", record:"8-9"},
  {week:16, home:false, opp:"GB", team_id:"NE", score_team:24, score_opp:31, result:"L", record:"8-9"},
  {week:17, home:true, opp:"DET", team_id:"NE", score_team:28, score_opp:21, result:"W", record:"8-9"},
  {week:18, home:false, opp:"NYJ", team_id:"NE", score_team:35, score_opp:14, result:"W", record:"8-9"}
];

export const demoScout = {
  team_id:"BUF",
  record:"10-7", 
  streak:"W2",
  last3:["W 24-17","W 20-10","L 21-27"],
  leaders:{QB:"J. Kingsley (OVR 84)", RB:"T. Morrow (82)", WR1:"K. Benton (87)"},
  injuries:["TE2 (ankle, Q)","CB1 (hamstring, D)"],
  tendencies:{run:42, pass:58, pace:62, aggression:55, blitz:31, man:48, zone:52}
};

export const demoPR = Array.from({length:32}, (_,i)=>({
  rank: i+1,
  team_id: ["SF","KC","BAL","BUF","PHI","DET","DAL","MIA","CIN","NE","NYJ","LAR","PIT","GB","SEA","HOU","JAX","CLE","MIN","NO","TB","ATL","IND","LAC","CHI","TEN","LV","NYG","ARI","WAS","DEN","CAR"][i],
  power: 1692 - i*9,
  delta: [ "+2","-1","+1","-2","+0","-1","+1","-3","+0","+2","-2","+1","+0","-1","+0","+1","+0","-2","+1","+0","-1","+0","+1","-1","+0","-1","+0","+1","-1","+0","+1","-1" ][i]
}));

export const demoBox = {
  home_id:"BUF", 
  away_id:"NE",
  q:[{NE:7,BUF:3},{NE:10,BUF:7},{NE:7,BUF:0},{NE:3,BUF:7}],
  totals:{NE:27, BUF:17}
};

// Helper function for API calls with fallback
export async function withDemo(fetcher, demo) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    
    const result = await fetcher(controller.signal);
    clearTimeout(timeoutId);
    
    if (!result || (Array.isArray(result) && result.length === 0)) {
      throw new Error('Empty response');
    }
    
    return { data: result, isDemo: false };
  } catch (error) {
    return { data: demo, isDemo: true };
  }
}
