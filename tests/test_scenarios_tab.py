"""
Tests for Scenarios tab functionality in the Streamlit harness.

Tests cover:
- Path sanitization
- Random seed generation
- Configuration persistence
- Scenario JSON loading/validation
- Scenario execution
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch
import tempfile
import shutil

# Import functions from app.py
import sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from streamlit_harness.app import (
    sanitize_basename,
    generate_random_seed,
    resolve_seed_value,
    load_config,
    save_config,
    load_scenario_json,
    save_report_to_path,
)


class TestPathSanitization:
    """Test suite for path sanitization functionality."""
    
    def test_sanitize_removes_forward_slashes(self):
        """Verify forward slashes are replaced with underscores."""
        result = sanitize_basename("test/with/slashes")
        assert "/" not in result
        assert result == "test_with_slashes"
    
    def test_sanitize_removes_backslashes(self):
        """Verify backslashes are replaced with underscores."""
        result = sanitize_basename("test\\with\\backslashes")
        assert "\\" not in result
        assert result == "test_with_backslashes"
    
    def test_sanitize_removes_parentheses(self):
        """Verify parentheses are removed."""
        result = sanitize_basename("test(with)parentheses")
        assert "(" not in result
        assert ")" not in result
        assert result == "testwithparentheses"
    
    def test_sanitize_removes_commas(self):
        """Verify commas are removed."""
        result = sanitize_basename("test,with,commas")
        assert "," not in result
        assert result == "testwithcommas"
    
    def test_sanitize_removes_periods(self):
        """Verify periods are removed."""
        result = sanitize_basename("test.with.periods")
        assert "." not in result
        assert result == "testwithperiods"
    
    def test_sanitize_removes_colons(self):
        """Verify colons are removed."""
        result = sanitize_basename("test:with:colons")
        assert ":" not in result
        assert result == "testwithcolons"
    
    def test_sanitize_replaces_multiplication_sign(self):
        """Verify × is replaced with 'x'."""
        result = sanitize_basename("test×multiplication")
        assert "×" not in result
        assert result == "testxmultiplication"
    
    def test_sanitize_replaces_spaces_with_underscores(self):
        """Verify spaces are replaced with underscores."""
        result = sanitize_basename("test with spaces")
        assert " " not in result
        assert result == "test_with_spaces"
    
    def test_sanitize_converts_to_lowercase(self):
        """Verify output is lowercase."""
        result = sanitize_basename("TestWithCAPSandNumbers123")
        assert result == "testwithcapsandnumbers123"
    
    def test_sanitize_collapses_multiple_underscores(self):
        """Verify multiple consecutive underscores are collapsed to one."""
        result = sanitize_basename("test___with___underscores")
        assert result == "test_with_underscores"
    
    def test_sanitize_strips_leading_trailing_underscores(self):
        """Verify leading and trailing underscores are removed."""
        result = sanitize_basename("_test_")
        assert result == "test"
    
    def test_sanitize_complex_scenario_name(self):
        """Test sanitization of complex real-world scenario name."""
        result = sanitize_basename("Presets × (Approach/Engage/Aftermath) × Normal")
        assert "/" not in result
        assert "(" not in result
        assert ")" not in result
        assert "×" not in result
        assert " " not in result
        # Spaces are replaced with underscores, × replaced with x
        assert result == "presets_x_approach_engage_aftermath_x_normal"
    
    def test_sanitize_removes_special_characters(self):
        """Verify all non-alphanumeric characters (except underscore) are removed."""
        result = sanitize_basename("test!@#$%^&*()+={}[]|;:'\",<>?/\\")
        # Should only contain alphanumeric and underscores
        assert all(c.isalnum() or c == '_' for c in result)
    
    def test_sanitize_empty_string(self):
        """Verify empty string handling."""
        result = sanitize_basename("")
        assert result == ""
    
    def test_sanitize_only_special_characters(self):
        """Verify string with only special characters returns empty."""
        result = sanitize_basename("().,/\\")
        assert result == ""


class TestRandomSeedGeneration:
    """Test suite for random seed generation."""
    
    def test_generate_random_seed_in_range(self):
        """Verify generated seeds are within valid range."""
        for _ in range(100):
            seed = generate_random_seed()
            assert 0 <= seed < 10**9
    
    def test_generate_random_seed_uniqueness(self):
        """Verify generated seeds vary (not always same)."""
        seeds = [generate_random_seed() for _ in range(10)]
        # Should have at least some variation
        assert len(set(seeds)) > 1
    
    def test_generate_random_seed_type(self):
        """Verify generated seed is an integer."""
        seed = generate_random_seed()
        assert isinstance(seed, int)


class TestSeedResolution:
    """Test suite for seed value resolution logic."""
    
    def test_resolve_integer_passthrough(self):
        """Verify integer seeds are passed through unchanged."""
        assert resolve_seed_value(42) == 42
        assert resolve_seed_value(0) == 0
        assert resolve_seed_value(999999999) == 999999999
    
    def test_resolve_random_string(self):
        """Verify 'random' string generates a seed."""
        seed = resolve_seed_value("random")
        assert isinstance(seed, int)
        assert 0 <= seed < 10**9
    
    def test_resolve_random_case_insensitive(self):
        """Verify 'random' is case-insensitive."""
        for variant in ["random", "Random", "RANDOM", "RaNdOm"]:
            seed = resolve_seed_value(variant)
            assert isinstance(seed, int)
            assert 0 <= seed < 10**9
    
    def test_resolve_none_generates_seed(self):
        """Verify None generates a random seed."""
        seed = resolve_seed_value(None)
        assert isinstance(seed, int)
        assert 0 <= seed < 10**9
    
    def test_resolve_numeric_string(self):
        """Verify numeric strings are converted to integers."""
        assert resolve_seed_value("123") == 123
        assert resolve_seed_value("0") == 0
    
    def test_resolve_invalid_string_generates_seed(self):
        """Verify invalid strings generate random seed."""
        seed = resolve_seed_value("not_a_number")
        assert isinstance(seed, int)
        assert 0 <= seed < 10**9


class TestConfigPersistence:
    """Test suite for configuration persistence."""
    
    def setup_method(self):
        """Create temporary directory for test configs."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".streamlit_harness_config.json"
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_config(self):
        """Verify config can be saved and loaded."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import save_config, load_config
            
            test_config = {
                "scenario_output_path": "test/path.json",
                "output_path_manually_edited": True,
            }
            save_config(test_config)
            
            loaded = load_config()
            assert loaded["scenario_output_path"] == "test/path.json"
            assert loaded["output_path_manually_edited"] is True
    
    def test_load_config_with_missing_file(self):
        """Verify default config is returned when file doesn't exist."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import load_config
            
            config = load_config()
            assert "scenario_output_path" in config
            assert config["scenario_output_path"] == "results/scenario_output.json"
    
    def test_load_config_with_invalid_json(self):
        """Verify defaults are returned when config file is invalid."""
        self.config_path.write_text("invalid json {{{")
        
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import load_config
            
            config = load_config()
            # Should return defaults on error
            assert "scenario_output_path" in config
    
    def test_save_config_creates_file(self):
        """Verify save_config creates the config file."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import save_config
            
            test_config = {"test_key": "test_value"}
            save_config(test_config)
            
            assert self.config_path.exists()
            content = json.loads(self.config_path.read_text())
            assert content["test_key"] == "test_value"
    
    def test_config_manual_edit_flag_persistence(self):
        """Verify manual edit flag persists correctly."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import save_config, load_config
            
            # Save config with flag set to True
            config = {"output_path_manually_edited": True}
            save_config(config)
            
            # Load and verify
            loaded = load_config()
            assert loaded.get("output_path_manually_edited") is True
            
            # Save with flag set to False
            config["output_path_manually_edited"] = False
            save_config(config)
            
            # Load and verify change
            loaded = load_config()
            assert loaded.get("output_path_manually_edited") is False


class TestScenarioLoading:
    """Test suite for scenario JSON loading and validation."""
    
    def test_load_valid_scenario(self):
        """Verify valid scenario JSON loads successfully."""
        valid_json = json.dumps({
            "name": "Test Scenario",
            "presets": ["dungeon"],
            "phases": ["engage"],
            "rarity_modes": ["normal"],
            "batch_size": 10,
            "base_seed": 42
        })
        
        scenario = load_scenario_json(valid_json)
        assert scenario["name"] == "Test Scenario"
        assert scenario["batch_size"] == 10
    
    def test_load_scenario_with_invalid_json(self):
        """Verify invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_scenario_json("not valid json {{{")
    
    def test_load_scenario_missing_required_fields(self):
        """Verify missing required fields raises ValueError."""
        # Missing 'base_seed'
        incomplete_json = json.dumps({
            "name": "Test",
            "presets": ["dungeon"],
            "phases": ["engage"],
            "rarity_modes": ["normal"],
            "batch_size": 10
        })
        
        with pytest.raises(ValueError, match="Missing required fields"):
            load_scenario_json(incomplete_json)
    
    def test_load_scenario_with_optional_fields(self):
        """Verify scenarios load with optional fields."""
        scenario_json = json.dumps({
            "name": "Test Scenario",
            "description": "Test description",
            "presets": ["dungeon"],
            "phases": ["engage"],
            "rarity_modes": ["normal"],
            "batch_size": 10,
            "base_seed": 42,
            "output_basename": "custom_name",
            "include_tags": "tag1,tag2",
            "exclude_tags": "tag3",
            "tick_between": False,
            "ticks_between": 5,
            "verbose": True
        })
        
        scenario = load_scenario_json(scenario_json)
        assert scenario["description"] == "Test description"
        assert scenario["output_basename"] == "custom_name"
        assert scenario["tick_between"] is False
        assert scenario["verbose"] is True


class TestReportSaving:
    """Test suite for report file saving functionality."""
    
    def setup_method(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_report_creates_directories(self):
        """Verify save_report_to_path creates necessary directories."""
        report = {"test": "data"}
        path = f"{self.temp_dir}/subdir1/subdir2/report.json"
        
        success, message = save_report_to_path(report, path)
        
        assert success
        assert Path(path).exists()
        assert "saved" in message.lower()
    
    def test_save_report_valid_json(self):
        """Verify saved report contains valid JSON."""
        report = {
            "suite": "Test Suite",
            "batch_n": 10,
            "runs": [{"test": "data"}]
        }
        path = f"{self.temp_dir}/report.json"
        
        success, _ = save_report_to_path(report, path)
        
        assert success
        loaded = json.loads(Path(path).read_text())
        assert loaded["suite"] == "Test Suite"
        assert loaded["batch_n"] == 10
    
    def test_save_report_overwrites_existing(self):
        """Verify existing files are overwritten."""
        path = f"{self.temp_dir}/report.json"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("old content")
        
        report = {"new": "data"}
        success, _ = save_report_to_path(report, path)
        
        assert success
        content = Path(path).read_text()
        assert "old content" not in content
        assert "new" in content
    
    def test_save_report_handles_errors(self):
        """Verify error handling for invalid paths."""
        report = {"test": "data"}
        # Try to save to a path that can't be created (e.g., /root on Unix without permissions)
        path = "/root/impossible/path/report.json"
        
        success, message = save_report_to_path(report, path)
        
        assert not success
        assert "failed" in message.lower()


class TestScenarioExecution:
    """Integration tests for scenario execution.
    
    These tests require the full engine to be importable.
    """
    
    def test_scenario_with_random_seed(self):
        """Verify scenarios can use 'random' base_seed."""
        scenario = {
            "name": "Random Test",
            "presets": ["dungeon"],
            "phases": ["engage"],
            "rarity_modes": ["normal"],
            "batch_size": 1,
            "base_seed": "random"
        }
        
        # The resolve_seed_value should handle this
        resolved = resolve_seed_value(scenario["base_seed"])
        assert isinstance(resolved, int)
        assert 0 <= resolved < 10**9
    
    def test_scenario_with_integer_seed(self):
        """Verify scenarios can use integer base_seed."""
        scenario = {
            "name": "Integer Test",
            "base_seed": 42
        }
        
        resolved = resolve_seed_value(scenario["base_seed"])
        assert resolved == 42


class TestPathPersistence:
    """Test suite for path persistence and manual edit tracking."""
    
    def setup_method(self):
        """Create temporary directory and config."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".streamlit_harness_config.json"
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manual_edit_flag_persists(self):
        """Verify manual edit flag is saved and loaded from config."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import save_config, load_config
            
            # Save with manual edit flag
            config = {
                "scenario_output_path": "custom/path.json",
                "output_path_manually_edited": True
            }
            save_config(config)
            
            # Load and verify flag persists
            loaded = load_config()
            assert loaded["output_path_manually_edited"] is True
    
    def test_default_manual_edit_flag(self):
        """Verify default value for manual edit flag."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import load_config
            
            # Load config with no manual edit flag set
            config = load_config()
            # Should default to False (or not present)
            assert config.get("output_path_manually_edited", False) is False
    
    def test_update_persistent_path_with_manual_edit(self):
        """Verify update_persistent_path sets manual edit flag when requested."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import update_persistent_path, load_config
            
            # Mock session state as a class with attributes
            class MockSessionState:
                def __setitem__(self, key, value):
                    setattr(self, key, value)
            
            with patch('streamlit_harness.app.st') as mock_st:
                mock_st.session_state = MockSessionState()
                
                # Update with manual_edit=True
                update_persistent_path("scenario_output_path", "new/path.json", manual_edit=True)
                
                # Verify flag was set in config
                config = load_config()
                assert config["output_path_manually_edited"] is True
                assert config["scenario_output_path"] == "new/path.json"
    
    def test_update_persistent_path_without_manual_edit(self):
        """Verify update_persistent_path doesn't set flag when manual_edit=False."""
        with patch('streamlit_harness.app.CONFIG_FILE', self.config_path):
            from streamlit_harness.app import update_persistent_path, load_config
            
            # Mock session state as a class with attributes
            class MockSessionState:
                def __setitem__(self, key, value):
                    setattr(self, key, value)
            
            with patch('streamlit_harness.app.st') as mock_st:
                mock_st.session_state = MockSessionState()
                
                # First set the flag to True
                config = {"output_path_manually_edited": True}
                from streamlit_harness.app import save_config
                save_config(config)
                
                # Update path without manual_edit flag
                update_persistent_path("scenario_output_path", "auto/generated.json", manual_edit=False)
                
                # Verify flag remains True (not overwritten)
                loaded = load_config()
                assert loaded["output_path_manually_edited"] is True


class TestScenarioValidation:
    """Test suite for scenario validation edge cases."""
    
    def test_scenario_all_required_fields_present(self):
        """Verify scenario validation passes with all required fields."""
        scenario_json = json.dumps({
            "name": "Valid Scenario",
            "presets": ["dungeon", "city"],
            "phases": ["approach", "engage"],
            "rarity_modes": ["calm", "normal"],
            "batch_size": 50,
            "base_seed": 1000
        })
        
        scenario = load_scenario_json(scenario_json)
        assert scenario["name"] == "Valid Scenario"
        assert len(scenario["presets"]) == 2
        assert len(scenario["phases"]) == 2
    
    def test_scenario_with_empty_arrays(self):
        """Verify scenario validates with empty arrays (edge case)."""
        scenario_json = json.dumps({
            "name": "Empty Arrays",
            "presets": [],
            "phases": [],
            "rarity_modes": [],
            "batch_size": 10,
            "base_seed": 42
        })
        
        # Should load without error (validation doesn't check array contents)
        scenario = load_scenario_json(scenario_json)
        assert scenario["presets"] == []
    
    def test_scenario_missing_multiple_fields(self):
        """Verify error message includes all missing fields."""
        incomplete_json = json.dumps({
            "name": "Incomplete"
            # Missing: presets, phases, rarity_modes, batch_size, base_seed
        })
        
        with pytest.raises(ValueError) as exc_info:
            load_scenario_json(incomplete_json)
        
        error_message = str(exc_info.value)
        assert "missing required fields" in error_message.lower()
        # Should list multiple missing fields
        assert "presets" in error_message
        assert "base_seed" in error_message


class TestRegressions:
    """Test suite to prevent regressions of previously fixed bugs."""
    
    def test_path_with_forward_slashes_no_nested_dirs(self):
        """Regression: Verify forward slashes don't create nested directories."""
        basename = "test/with/slashes"
        sanitized = sanitize_basename(basename)
        
        # Should not contain any path separators
        assert "/" not in sanitized
        assert "\\" not in sanitized
        # Should be flat (no directory structure)
        assert sanitized == "test_with_slashes"
    
    def test_scenario_name_with_parentheses_no_nested_dirs(self):
        """Regression: Verify parentheses don't create nested directories."""
        basename = "Presets × (Approach/Engage) × Normal"
        sanitized = sanitize_basename(basename)
        
        # Should not contain parentheses or slashes
        assert "(" not in sanitized
        assert ")" not in sanitized
        assert "/" not in sanitized
    
    def test_manual_path_preserved_on_scenario_switch(self):
        """Regression: Verify manual paths persist when switching scenarios."""
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / ".streamlit_harness_config.json"
        
        try:
            with patch('streamlit_harness.app.CONFIG_FILE', config_path):
                from streamlit_harness.app import save_config, load_config
                
                # Simulate user manually editing path
                config = {
                    "scenario_output_path": "scenarios/results/custom_path.json",
                    "output_path_manually_edited": True
                }
                save_config(config)
                
                # Simulate loading config (like switching scenarios)
                loaded = load_config()
                
                # Path should be preserved
                assert loaded["scenario_output_path"] == "scenarios/results/custom_path.json"
                # Manual edit flag should also be preserved
                assert loaded["output_path_manually_edited"] is True
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
