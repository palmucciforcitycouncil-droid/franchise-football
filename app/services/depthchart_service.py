"""
Depth Chart Service with Persistence and Constraints
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlmodel import Session, select, delete
from fastapi import HTTPException

from app.models.depthchart import (
    DepthChartEntry, 
    DepthSlotDTO, 
    DepthChartDTO,
    DEPTH_CHART_SLOTS,
    POSITION_GROUPS,
    group_for_slot
)

class DepthChartService:
    """Service for managing depth charts with persistence and constraints"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_depthchart(self, team_id: str, season: int) -> DepthChartDTO:
        """Get current depth chart for team/season"""
        # Get existing entries from database
        stmt = select(DepthChartEntry).where(
            DepthChartEntry.team_id == team_id,
            DepthChartEntry.season == season
        )
        entries = self.db.exec(stmt).all()
        
        # Convert to slots with player names
        slots = []
        for entry in entries:
            slot = DepthSlotDTO(
                position=entry.position,
                slot=entry.slot,
                player_id=entry.player_id,
                name=self._get_player_name(entry.player_id) if entry.player_id else None,
                ovr=self._get_player_ovr(entry.player_id) if entry.player_id else None
            )
            slots.append(slot)
        
        # Fill in empty slots for completeness
        all_slots = self._get_all_required_slots()
        existing_slot_names = {slot.slot for slot in slots}
        
        for position, slot_list in all_slots.items():
            for slot_name in slot_list:
                if slot_name not in existing_slot_names:
                    slots.append(DepthSlotDTO(
                        position=position,
                        slot=slot_name,
                        player_id=None,
                        name=None,
                        ovr=None
                    ))
        
        return DepthChartDTO(
            team_id=team_id,
            season=season,
            slots=slots,
            warnings=None
        )
    
    def set_depth_slot(self, team_id: str, season: int, position: str, slot: str, player_id: Optional[int]) -> DepthChartDTO:
        """Set a single depth slot with constraint validation"""
        # Validate no duplicate in same position group
        if player_id is not None:
            group = group_for_slot(slot)
            existing_in_group = self._get_player_in_group(team_id, season, group, player_id)
            if existing_in_group and existing_in_group.slot != slot:
                raise HTTPException(
                    status_code=409,
                    detail=f"Player {player_id} is already assigned to {existing_in_group.slot} in the {group} group"
                )
        
        # Upsert the entry
        stmt = select(DepthChartEntry).where(
            DepthChartEntry.team_id == team_id,
            DepthChartEntry.season == season,
            DepthChartEntry.slot == slot
        )
        entry = self.db.exec(stmt).first()
        
        if entry:
            # Update existing
            entry.player_id = player_id
            entry.updated_at = datetime.utcnow()
        else:
            # Create new
            entry = DepthChartEntry(
                team_id=team_id,
                season=season,
                position=position,
                slot=slot,
                player_id=player_id
            )
            self.db.add(entry)
        
        self.db.commit()
        self.db.refresh(entry)
        
        return self.get_depthchart(team_id, season)
    
    def set_depth_bulk(self, team_id: str, season: int, slots: List[Dict]) -> DepthChartDTO:
        """Set entire depth chart with bulk validation"""
        # Validate no duplicates within position groups
        self._validate_bulk_slots(team_id, season, slots)
        
        # Clear existing entries for this team/season
        stmt = delete(DepthChartEntry).where(
            DepthChartEntry.team_id == team_id,
            DepthChartEntry.season == season
        )
        self.db.exec(stmt)
        
        # Insert new entries
        for slot_data in slots:
            entry = DepthChartEntry(
                team_id=team_id,
                season=season,
                position=slot_data["position"],
                slot=slot_data["slot"],
                player_id=slot_data.get("player_id")
            )
            self.db.add(entry)
        
        self.db.commit()
        
        return self.get_depthchart(team_id, season)
    
    def auto_fill(self, team_id: str, season: int) -> Tuple[DepthChartDTO, List[str]]:
        """Auto-fill empty slots only, with warnings"""
        warnings = []
        
        # Get current chart to see what's already filled
        current_chart = self.get_depthchart(team_id, season)
        filled_slots = {slot.slot: slot.player_id for slot in current_chart.slots if slot.player_id is not None}
        
        # Get roster data
        roster = self._get_team_roster(team_id, season)
        players_by_position = self._group_players_by_position(roster)
        
        # Auto-fill empty slots only
        updates_made = False
        for position, slot_list in DEPTH_CHART_SLOTS.items():
            available_players = players_by_position.get(position, [])
            if not available_players:
                warnings.append(f"No {position} players available on roster")
                continue
            
            # Sort available players by OVR desc, POT desc, age asc
            sorted_players = sorted(
                available_players,
                key=lambda p: (-p.get('overall_rating', 0), -p.get('potential', 0), p.get('age', 999))
            )
            
            # Track which players we've already assigned in this auto-fill
            assigned_players = set()
            
            # Assign to empty slots only
            for slot in slot_list:
                if slot not in filled_slots:  # Only fill empty slots
                    # Find the best available player for this slot
                    assigned = False
                    for player in sorted_players:
                        if player['id'] not in assigned_players:
                            # Check if this player is already used in this position group (from existing assignments)
                            group = group_for_slot(slot)
                            existing_slot = self._get_player_in_group(team_id, season, group, player['id'])
                            
                            if existing_slot is None:
                                # Safe to assign
                                self.set_depth_slot(team_id, season, position, slot, player['id'])
                                assigned_players.add(player['id'])
                                updates_made = True
                                assigned = True
                                break
                            else:
                                # Player already used in this group, skip
                                warnings.append(f"Player {player['name']} already assigned to {existing_slot.slot}")
                    
                    if not assigned:
                        warnings.append(f"No available {position} players for {slot}")
        
        # Get updated chart
        updated_chart = self.get_depthchart(team_id, season)
        
        if not updates_made:
            warnings.append("No empty slots found to auto-fill")
        
        return updated_chart, warnings
    
    def _validate_bulk_slots(self, team_id: str, season: int, slots: List[Dict]):
        """Validate that no player appears twice in the same position group"""
        group_assignments = {}  # group -> {player_id: slot}
        
        for slot_data in slots:
            player_id = slot_data.get("player_id")
            if player_id is None:
                continue
                
            slot = slot_data["slot"]
            group = group_for_slot(slot)
            
            if group not in group_assignments:
                group_assignments[group] = {}
            
            if player_id in group_assignments[group]:
                existing_slot = group_assignments[group][player_id]
                raise HTTPException(
                    status_code=409,
                    detail=f"Player {player_id} cannot be assigned to both {existing_slot} and {slot} in the {group} group"
                )
            
            group_assignments[group][player_id] = slot
    
    def _get_player_in_group(self, team_id: str, season: int, group: str, player_id: int) -> Optional[DepthChartEntry]:
        """Get existing assignment of a player within a position group"""
        group_slots = POSITION_GROUPS.get(group, [])
        if not group_slots:
            return None
            
        stmt = select(DepthChartEntry).where(
            DepthChartEntry.team_id == team_id,
            DepthChartEntry.season == season,
            DepthChartEntry.slot.in_(group_slots),
            DepthChartEntry.player_id == player_id
        )
        return self.db.exec(stmt).first()
    
    def _get_all_required_slots(self) -> Dict[str, List[str]]:
        """Get all required slots organized by position"""
        return DEPTH_CHART_SLOTS.copy()
    
    def _get_player_name(self, player_id: int) -> Optional[str]:
        """Get player name by ID (mock implementation)"""
        # In real implementation, this would query the players table
        mock_players = {
            212: "J. Kingsley",
            213: "M. Sanders", 
            332: "T. Morrow",
            411: "K. Carter",
            101: "K. Benton",
            234: "L. Carter",
            456: "J. Thomas",
            567: "C. Matthews",
            678: "B. Wilson",
            789: "D. Miller",
            890: "M. Johnson",
            901: "T. Garcia",
            102: "K. Brown",
            103: "J. Davis",
            104: "R. Anderson",
            105: "P. Williams",
            106: "S. Taylor",
            107: "L. Jackson",
            108: "E. Harris",
            109: "M. White",
            110: "C. Robinson",
            111: "D. Lewis",
            112: "T. Young",
            113: "A. Green",
            114: "J. Adams",
            115: "N. Parker",
            116: "B. Collins"
        }
        return mock_players.get(player_id)
    
    def _get_player_ovr(self, player_id: int) -> Optional[int]:
        """Get player OVR by ID (mock implementation)"""
        # In real implementation, this would query the players table
        mock_ovr = {
            212: 84, 213: 71, 332: 82, 411: 76, 101: 87, 234: 83, 456: 74,
            567: 85, 678: 77, 789: 82, 890: 79, 901: 81, 102: 80, 103: 83,
            104: 84, 105: 80, 106: 82, 107: 85, 108: 83, 109: 78, 110: 86,
            111: 84, 112: 76, 113: 85, 114: 82, 115: 79, 116: 77
        }
        return mock_ovr.get(player_id)
    
    def _get_team_roster(self, team_id: str, season: int) -> List[Dict]:
        """Get team roster (mock implementation)"""
        mock_roster = [
            {"id": 212, "name": "J. Kingsley", "position": "QB", "overall_rating": 84, "potential": 88, "age": 28},
            {"id": 213, "name": "M. Sanders", "position": "QB", "overall_rating": 71, "potential": 82, "age": 24},
            {"id": 332, "name": "T. Morrow", "position": "RB", "overall_rating": 82, "potential": 85, "age": 26},
            {"id": 411, "name": "K. Carter", "position": "RB", "overall_rating": 76, "potential": 83, "age": 23},
            {"id": 101, "name": "K. Benton", "position": "WR", "overall_rating": 87, "potential": 90, "age": 27},
            {"id": 234, "name": "L. Carter", "position": "WR", "overall_rating": 83, "potential": 87, "age": 25},
            {"id": 456, "name": "J. Thomas", "position": "WR", "overall_rating": 74, "potential": 85, "age": 22},
            {"id": 567, "name": "C. Matthews", "position": "TE", "overall_rating": 85, "potential": 86, "age": 27},
            {"id": 678, "name": "B. Wilson", "position": "TE", "overall_rating": 77, "potential": 82, "age": 24},
            
            # Offensive Line
            {"id": 789, "name": "D. Miller", "position": "LT", "overall_rating": 82, "potential": 86, "age": 25},
            {"id": 890, "name": "M. Johnson", "position": "LG", "overall_rating": 79, "potential": 84, "age": 26},
            {"id": 901, "name": "T. Garcia", "position": "C", "overall_rating": 81, "potential": 80, "age": 29},
            {"id": 102, "name": "K. Brown", "position": "RG", "overall_rating": 80, "potential": 81, "age": 28},
            {"id": 103, "name": "J. Davis", "position": "RT", "overall_rating": 83, "potential": 84, "age": 27},
            
            # Defensive Line
            {"id": 104, "name": "R. Anderson", "position": "LDE", "overall_rating": 84, "potential": 87, "age": 26},
            {"id": 105, "name": "P. Williams", "position": "DT", "overall_rating": 80, "potential": 83, "age": 27},
            {"id": 106, "name": "S. Taylor", "position": "RDE", "overall_rating": 82, "potential": 81, "age": 29},
            
            # Linebackers
            {"id": 107, "name": "L. Jackson", "position": "MLB", "overall_rating": 85, "potential": 88, "age": 25},
            {"id": 108, "name": "E. Harris", "position": "MLB", "overall_rating": 83, "potential": 82, "age": 28},
            {"id": 109, "name": "M. White", "position": "OLB", "overall_rating": 78, "potential": 84, "age": 24},
            {"id": 117, "name": "A. Smith", "position": "OLB", "overall_rating": 81, "potential": 83, "age": 26},
            
            # Defensive Backs
            {"id": 110, "name": "C. Robinson", "position": "CB", "overall_rating": 86, "potential": 88, "age": 26},
            {"id": 111, "name": "D. Lewis", "position": "CB", "overall_rating": 84, "potential": 85, "age": 27},
            {"id": 112, "name": "T. Young", "position": "CB", "overall_rating": 76, "potential": 86, "age": 23},
            {"id": 113, "name": "A. Green", "position": "FS", "overall_rating": 85, "potential": 84, "age": 28},
            {"id": 114, "name": "J. Adams", "position": "SS", "overall_rating": 82, "potential": 86, "age": 25},
            
            # Special Teams
            {"id": 115, "name": "N. Parker", "position": "K", "overall_rating": 79, "potential": 82, "age": 26},
            {"id": 116, "name": "B. Collins", "position": "P", "overall_rating": 77, "potential": 76, "age": 29},
        ]
        return mock_roster
    
    def _group_players_by_position(self, roster: List[Dict]) -> Dict[str, List[Dict]]:
        """Group players by position"""
        grouped = {}
        for player in roster:
            position = player.get('position')
            if position:
                if position not in grouped:
                    grouped[position] = []
                grouped[position].append(player)
        return grouped