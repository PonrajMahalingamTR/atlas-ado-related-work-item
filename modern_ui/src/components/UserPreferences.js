import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Switch,
  Button,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

const UserPreferences = ({ onPreferencesChange }) => {
  const [preferences, setPreferences] = useState({
    autoSelectTeam: true,
    selectionMethod: 'hybrid', // 'profile', 'workitem_count', 'hybrid'
    showSelectionReason: true,
    allowAutoSelectionOverride: true,
    timeRange: 'last_30_days',
    minWorkItems: 1,
    includeInactiveTeams: false,
  });
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/user/profile');
      if (response.ok) {
        const data = await response.json();
        if (data.preferences) {
          setPreferences(prev => ({ ...prev, ...data.preferences }));
        }
      }
    } catch (error) {
      console.error('Error loading preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const savePreferences = async () => {
    setSaving(true);
    setMessage('');
    
    try {
      const response = await fetch('/api/user/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          preferences: preferences
        })
      });

      if (response.ok) {
        setMessage('Preferences saved successfully!');
        if (onPreferencesChange) {
          onPreferencesChange(preferences);
        }
        setTimeout(() => setMessage(''), 3000);
      } else {
        throw new Error('Failed to save preferences');
      }
    } catch (error) {
      setMessage(`Error saving preferences: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handlePreferenceChange = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">Team Selection Preferences</Typography>
      </Box>

      {message && (
        <Alert 
          severity={message.includes('Error') ? 'error' : 'success'} 
          sx={{ mb: 3 }}
        >
          {message}
        </Alert>
      )}

      {/* Auto-selection Settings */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Auto-Selection Settings
        </Typography>
        
        <FormControlLabel
          control={
            <Switch
              checked={preferences.autoSelectTeam}
              onChange={(e) => handlePreferenceChange('autoSelectTeam', e.target.checked)}
            />
          }
          label="Enable automatic team selection"
        />
        
        <FormControlLabel
          control={
            <Switch
              checked={preferences.showSelectionReason}
              onChange={(e) => handlePreferenceChange('showSelectionReason', e.target.checked)}
            />
          }
          label="Show selection reason and confidence"
        />
        
        <FormControlLabel
          control={
            <Switch
              checked={preferences.allowAutoSelectionOverride}
              onChange={(e) => handlePreferenceChange('allowAutoSelectionOverride', e.target.checked)}
            />
          }
          label="Allow manual team override"
        />
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Selection Method */}
      <Box sx={{ mb: 3 }}>
        <FormControl component="fieldset">
          <FormLabel component="legend">Selection Method</FormLabel>
          <RadioGroup
            value={preferences.selectionMethod}
            onChange={(e) => handlePreferenceChange('selectionMethod', e.target.value)}
          >
            <FormControlLabel
              value="profile"
              control={<Radio />}
              label="User Profile Preference (if set)"
            />
            <FormControlLabel
              value="workitem_count"
              control={<Radio />}
              label="Work Item Activity Analysis"
            />
            <FormControlLabel
              value="hybrid"
              control={<Radio />}
              label="Hybrid (Profile + Activity Analysis)"
            />
          </RadioGroup>
        </FormControl>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Analysis Settings */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Analysis Settings
        </Typography>
        
        <FormControl component="fieldset" sx={{ mb: 2 }}>
          <FormLabel component="legend">Time Range</FormLabel>
          <RadioGroup
            value={preferences.timeRange}
            onChange={(e) => handlePreferenceChange('timeRange', e.target.value)}
          >
            <FormControlLabel
              value="last_7_days"
              control={<Radio />}
              label="Last 7 days"
            />
            <FormControlLabel
              value="last_30_days"
              control={<Radio />}
              label="Last 30 days"
            />
            <FormControlLabel
              value="last_90_days"
              control={<Radio />}
              label="Last 90 days"
            />
          </RadioGroup>
        </FormControl>

        <FormControlLabel
          control={
            <Switch
              checked={preferences.includeInactiveTeams}
              onChange={(e) => handlePreferenceChange('includeInactiveTeams', e.target.checked)}
            />
          }
          label="Include inactive teams in analysis"
        />
      </Box>

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadPreferences}
          disabled={loading}
        >
          Reset
        </Button>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={savePreferences}
          disabled={saving}
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
            },
            '&.Mui-disabled': {
              background: 'rgba(0,0,0,0.12)',
              color: 'rgba(0,0,0,0.26)',
            }
          }}
        >
          {saving ? 'Saving...' : 'Save Preferences'}
        </Button>
      </Box>
    </Paper>
  );
};

export default UserPreferences;

