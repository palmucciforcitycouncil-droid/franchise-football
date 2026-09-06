export type ColDef = {
  key: string;              // unique stable key (e.g., "ovr", "spd")
  label: string;            // header label (e.g., "OVR")
  width?: number;           // preferred width px
  minWidth?: number;        // min px
  maxWidth?: number;        // max px
  align?: "left"|"right"|"center";
  tooltip?: string;
  group?: string;           // for Stats view blocks ("QB","RB","REC","DEF","ST","CORE")
  numeric?: boolean;        // true => right-align
  fixed?: boolean;          // true => non-draggable (Name column only)
}

export const attributesColumns: ColDef[] = [
  {
    key: "name",
    label: "Name",
    width: 180,
    minWidth: 140,
    maxWidth: 220,
    align: "left",
    tooltip: "Player name and position",
    fixed: true
  },
  {
    key: "ovr",
    label: "OVR",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Overall rating",
    numeric: true
  },
  {
    key: "spd",
    label: "SPD",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Speed",
    numeric: true
  },
  {
    key: "str",
    label: "STR",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Strength",
    numeric: true
  },
  {
    key: "agi",
    label: "AGI",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Agility",
    numeric: true
  },
  {
    key: "tpw",
    label: "TPW",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Throw Power",
    numeric: true
  },
  {
    key: "tac",
    label: "TAC",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Throwing Accuracy",
    numeric: true
  },
  {
    key: "cth",
    label: "CTH",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Catching",
    numeric: true
  },
  {
    key: "tck",
    label: "TCK",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Tackling",
    numeric: true
  },
  {
    key: "awr",
    label: "AWR",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Awareness",
    numeric: true
  },
  {
    key: "pot",
    label: "POT",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Potential",
    numeric: true
  },
  {
    key: "sta",
    label: "STA",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Stamina - Minor in-game performance impact only",
    numeric: true
  },
  {
    key: "inj",
    label: "INJ",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Injury",
    numeric: true
  },
  {
    key: "mor",
    label: "MOR",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Morale",
    numeric: true
  },
  {
    key: "age",
    label: "AGE",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Age",
    numeric: true
  },
  {
    key: "ctr",
    label: "CTR",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Contract",
    numeric: true
  },
  {
    key: "yrs",
    label: "YRS",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Years",
    numeric: true
  },
  {
    key: "dep",
    label: "DEP",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Depth",
    numeric: true
  },
  {
    key: "hlth",
    label: "HLTH",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Health",
    numeric: true
  },
  {
    key: "trd",
    label: "TRD",
    width: 60,
    minWidth: 50,
    maxWidth: 70,
    align: "center",
    tooltip: "Trade Value",
    numeric: true
  }
];
