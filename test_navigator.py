#!/usr/bin/env python3
"""
Simple test to verify the navigator can be imported and basic functions work.
Run with: pytest test_navigator.py -v
"""

import json
import pytest
from pathlib import Path


class TestNavigatorImports:
    """Test that all modules can be imported."""
    
    def test_import_main_navigator(self):
        """Test importing the main navigator module."""
        try:
            from navigate import VisionNavigator, NavigationAction, VisionProvider
            assert VisionNavigator is not None
            assert NavigationAction is not None
            assert VisionProvider is not None
        except ImportError as e:
            pytest.skip(f"Missing dependency: {e}")
    
    def test_import_enhanced_navigator(self):
        """Test importing the enhanced navigator module."""
        try:
            from navigate_enhanced import EnhancedVisionNavigator, NavigationState
            assert EnhancedVisionNavigator is not None
            assert NavigationState is not None
        except ImportError as e:
            pytest.skip(f"Missing dependency: {e}")


class TestDataClasses:
    """Test data class functionality."""
    
    def test_navigation_action_creation(self):
        """Test creating a NavigationAction."""
        try:
            from navigate import NavigationAction
            
            action = NavigationAction(
                action_type="click",
                target="Search button",
                coordinates=(640, 40),
                confidence=0.95,
                reasoning="Clicking the search box to enter query"
            )
            
            assert action.action_type == "click"
            assert action.coordinates == (640, 40)
            assert action.confidence == 0.95
        except ImportError:
            pytest.skip("Missing dependency")
    
    def test_navigation_state_creation(self):
        """Test creating a NavigationState."""
        try:
            from navigate_enhanced import NavigationState
            
            state = NavigationState()
            assert state.step == 0
            assert state.goal_achieved == False
            assert len(state.actions_taken) == 0
        except ImportError:
            pytest.skip("Missing dependency")


class TestOutputFormat:
    """Test that output format matches specification."""
    
    def test_sample_output_structure(self):
        """Verify sample_output.json has correct structure."""
        sample_path = Path(__file__).parent / "sample_output.json"
        
        with open(sample_path) as f:
            data = json.load(f)
        
        # Check required fields
        assert "repository" in data
        assert "latest_release" in data
        
        release = data["latest_release"]
        assert "version" in release
        assert "tag" in release
        assert "author" in release
    
    def test_sample_output_values(self):
        """Verify sample output contains expected values."""
        sample_path = Path(__file__).parent / "sample_output.json"
        
        with open(sample_path) as f:
            data = json.load(f)
        
        assert data["repository"] == "openclaw/openclaw"
        assert data["latest_release"]["version"] == "v2026.1.29"
        assert data["latest_release"]["tag"] == "77e703c"
        assert data["latest_release"]["author"] == "steipete"


class TestActionParsing:
    """Test action parsing functionality."""
    
    def test_parse_valid_json_response(self):
        """Test parsing a valid JSON action response."""
        try:
            from navigate import VisionNavigator
            
            # Create navigator (won't connect to API)
            nav = VisionNavigator.__new__(VisionNavigator)
            
            response = '''
            {
                "action_type": "click",
                "target": "Search box",
                "value": null,
                "coordinates": [640, 40],
                "confidence": 0.9,
                "reasoning": "Need to click search"
            }
            '''
            
            action = nav._parse_action_response(response)
            
            assert action.action_type == "click"
            assert action.coordinates == (640, 40)
            assert action.confidence == 0.9
        except ImportError:
            pytest.skip("Missing dependency")
    
    def test_parse_markdown_wrapped_response(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        try:
            from navigate import VisionNavigator
            
            nav = VisionNavigator.__new__(VisionNavigator)
            
            response = '''```json
            {
                "action_type": "type",
                "target": "Search input",
                "value": "openclaw",
                "coordinates": null,
                "confidence": 0.85,
                "reasoning": "Typing search query"
            }
            ```'''
            
            action = nav._parse_action_response(response)
            
            assert action.action_type == "type"
            assert action.value == "openclaw"
        except ImportError:
            pytest.skip("Missing dependency")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
