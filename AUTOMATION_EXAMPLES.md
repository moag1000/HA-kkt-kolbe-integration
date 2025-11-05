# Automation Examples for KKT Kolbe Integration

This document provides practical automation examples for your KKT Kolbe devices in Home Assistant.

## Table of Contents
- [Hood Automations](#hood-automations)
- [Cooktop Automations](#cooktop-automations)
- [Combined Automations](#combined-automations)
- [Advanced Use Cases](#advanced-use-cases)

---

## Hood Automations

### 1. Auto-Start Hood When Cooktop is Active

Automatically turn on the hood when you start cooking.

```yaml
automation:
  - alias: "Kitchen: Auto-start hood when cooking"
    trigger:
      - platform: state
        entity_id: switch.ind7705hc_power
        to: "on"
    action:
      - service: switch.turn_on
        entity_id: switch.hermes_style_power
      - service: select.select_option
        target:
          entity_id: select.hermes_style_fan_speed
        data:
          option: "low"
```

### 2. Smart Fan Speed Based on Cooktop Power

Adjust hood fan speed based on how many cooking zones are active.

```yaml
automation:
  - alias: "Kitchen: Smart hood fan speed"
    trigger:
      - platform: state
        entity_id:
          - number.zone_1_power_level
          - number.zone_2_power_level
          - number.zone_3_power_level
          - number.zone_4_power_level
          - number.zone_5_power_level
    variables:
      total_power: >
        {{ states('number.zone_1_power_level')|int(0) +
           states('number.zone_2_power_level')|int(0) +
           states('number.zone_3_power_level')|int(0) +
           states('number.zone_4_power_level')|int(0) +
           states('number.zone_5_power_level')|int(0) }}
    action:
      - choose:
          - conditions: "{{ total_power == 0 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.hermes_style_fan_speed
                data:
                  option: "off"
          - conditions: "{{ total_power < 20 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.hermes_style_fan_speed
                data:
                  option: "low"
          - conditions: "{{ total_power < 50 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.hermes_style_fan_speed
                data:
                  option: "middle"
          - conditions: "{{ total_power < 80 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.hermes_style_fan_speed
                data:
                  option: "high"
        default:
          - service: select.select_option
            target:
              entity_id: select.hermes_style_fan_speed
            data:
              option: "strong"
```

### 3. Auto-Stop Hood After Cooking

Turn off the hood automatically 5 minutes after all zones are off.

```yaml
automation:
  - alias: "Kitchen: Auto-stop hood after cooking"
    trigger:
      - platform: state
        entity_id: switch.ind7705hc_power
        to: "off"
        for:
          minutes: 5
    action:
      - service: switch.turn_off
        entity_id: switch.hermes_style_power
```

### 4. Filter Reminder Notification

Get notified when it's time to clean the hood filter.

```yaml
automation:
  - alias: "Kitchen: Hood filter cleaning reminder"
    trigger:
      - platform: state
        entity_id: switch.hermes_style_filter_cleaning_reminder
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Hood Filter Reminder"
          message: "Time to clean the hood filter!"
          data:
            actions:
              - action: "RESET_FILTER"
                title: "Mark as cleaned"
```

### 5. Evening Ambient Lighting

Set hood lighting to a specific RGB mode in the evening.

```yaml
automation:
  - alias: "Kitchen: Evening ambient hood lighting"
    trigger:
      - platform: sun
        event: sunset
    condition:
      - condition: state
        entity_id: switch.hermes_style_power
        state: "off"
    action:
      - service: switch.turn_on
        entity_id: switch.hermes_style_light
      - service: number.set_value
        target:
          entity_id: number.hermes_style_rgb_mode
        data:
          value: 3  # Scene mode
```

---

## Cooktop Automations

### 6. Child Lock Automation

Automatically enable child lock when nobody is home.

```yaml
automation:
  - alias: "Kitchen: Enable cooktop child lock when away"
    trigger:
      - platform: state
        entity_id: zone.home
        to: "0"  # Nobody home
        for:
          minutes: 10
    condition:
      - condition: state
        entity_id: switch.ind7705hc_power
        state: "off"
    action:
      - service: switch.turn_on
        entity_id: switch.ind7705hc_child_lock
```

### 7. Safety Timer Warning

Alert when a zone has been on for too long without timer.

```yaml
automation:
  - alias: "Kitchen: Long cooking warning"
    trigger:
      - platform: state
        entity_id:
          - number.zone_1_power_level
          - number.zone_2_power_level
          - number.zone_3_power_level
        from: "0"
        for:
          hours: 2
    condition:
      - condition: template
        value_template: "{{ states(trigger.entity_id)|int > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Cooktop Safety Warning"
          message: "Zone {{ trigger.entity_id.split('_')[1] }} has been on for 2 hours!"
          data:
            priority: high
```

### 8. Boost Mode Auto-Disable

Automatically disable boost mode after 10 minutes to save energy.

```yaml
automation:
  - alias: "Kitchen: Auto-disable boost mode"
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.zone_1_boost_active
          - binary_sensor.zone_2_boost_active
          - binary_sensor.zone_3_boost_active
          - binary_sensor.zone_4_boost_active
          - binary_sensor.zone_5_boost_active
        to: "on"
        for:
          minutes: 10
    action:
      # Note: Boost disable might need to be done via zone power level adjustment
      - service: notify.mobile_app
        data:
          title: "Boost Mode"
          message: "Zone {{ trigger.entity_id.split('_')[1] }} boost mode has been on for 10 minutes"
```

### 9. Error Detection and Notification

Alert when any cooking zone reports an error.

```yaml
automation:
  - alias: "Kitchen: Cooktop error alert"
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.zone_1_error
          - binary_sensor.zone_2_error
          - binary_sensor.zone_3_error
          - binary_sensor.zone_4_error
          - binary_sensor.zone_5_error
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Cooktop Error"
          message: "Error detected on {{ trigger.to_state.name }}"
          data:
            priority: high
            sound: alert
```

### 10. Senior Mode Schedule

Enable senior mode (simplified controls) during specific hours.

```yaml
automation:
  - alias: "Kitchen: Enable senior mode in evening"
    trigger:
      - platform: time
        at: "20:00:00"
    action:
      - service: switch.turn_on
        entity_id: switch.ind7705hc_senior_mode

  - alias: "Kitchen: Disable senior mode in morning"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: switch.turn_off
        entity_id: switch.ind7705hc_senior_mode
```

---

## Combined Automations

### 11. Complete Cooking Scene

Start cooking with optimal settings.

```yaml
script:
  start_cooking:
    alias: "Start Cooking"
    sequence:
      # Turn on cooktop
      - service: switch.turn_on
        entity_id: switch.ind7705hc_power
      # Turn on hood
      - service: switch.turn_on
        entity_id: switch.hermes_style_power
      # Set hood to low initially
      - service: select.select_option
        target:
          entity_id: select.hermes_style_fan_speed
        data:
          option: "low"
      # Turn on hood light
      - service: switch.turn_on
        entity_id: switch.hermes_style_light
      # Disable child lock
      - service: switch.turn_off
        entity_id: switch.ind7705hc_child_lock
      # Send notification
      - service: notify.mobile_app
        data:
          message: "Kitchen ready for cooking"
```

### 12. End Cooking Scene

Clean shutdown after cooking.

```yaml
script:
  end_cooking:
    alias: "End Cooking"
    sequence:
      # Turn off all cooktop zones
      - service: number.set_value
        target:
          entity_id:
            - number.zone_1_power_level
            - number.zone_2_power_level
            - number.zone_3_power_level
            - number.zone_4_power_level
            - number.zone_5_power_level
        data:
          value: 0
      # Keep hood running for 5 more minutes
      - delay:
          minutes: 5
      # Turn off hood
      - service: switch.turn_off
        entity_id: switch.hermes_style_power
      # Turn off cooktop
      - service: switch.turn_off
        entity_id: switch.ind7705hc_power
      # Enable child lock
      - service: switch.turn_on
        entity_id: switch.ind7705hc_child_lock
```

---

## Advanced Use Cases

### 13. Energy Monitoring Integration

Track cooking energy usage over time.

```yaml
sensor:
  - platform: template
    sensors:
      cooking_energy_today:
        friendly_name: "Cooking Energy Today"
        unit_of_measurement: "kWh"
        value_template: >
          {% set zones = [
            'number.zone_1_power_level',
            'number.zone_2_power_level',
            'number.zone_3_power_level',
            'number.zone_4_power_level',
            'number.zone_5_power_level'
          ] %}
          {% set total_power = namespace(value=0) %}
          {% for zone in zones %}
            {% set total_power.value = total_power.value + (states(zone)|int(0) * 0.2) %}
          {% endfor %}
          {{ (total_power.value / 1000) | round(2) }}

utility_meter:
  daily_cooking_energy:
    source: sensor.cooking_energy_today
    cycle: daily
```

### 14. Voice Control Integration

Control your appliances with voice commands (Google Home/Alexa).

```yaml
# Example for Google Home
intent_script:
  StartCooking:
    speech:
      text: "Starting the kitchen for cooking"
    action:
      - service: script.start_cooking

  StopCooking:
    speech:
      text: "Shutting down the kitchen"
    action:
      - service: script.end_cooking

  SetHoodFan:
    speech:
      text: "Setting hood fan to {{ speed }}"
    action:
      - service: select.select_option
        target:
          entity_id: select.hermes_style_fan_speed
        data:
          option: "{{ speed }}"
```

### 15. Dashboard Card Example

Lovelace card for complete kitchen control.

```yaml
type: vertical-stack
cards:
  - type: entities
    title: "Cooktop Control"
    entities:
      - entity: switch.ind7705hc_power
      - entity: switch.ind7705hc_pause
      - entity: switch.ind7705hc_child_lock
      - type: divider
      - entity: number.zone_1_power_level
      - entity: number.zone_2_power_level
      - entity: number.zone_3_power_level
      - entity: number.zone_4_power_level
      - entity: number.zone_5_power_level

  - type: entities
    title: "Hood Control"
    entities:
      - entity: switch.hermes_style_power
      - entity: select.hermes_style_fan_speed
      - entity: switch.hermes_style_light
      - entity: number.hermes_style_timer
      - entity: sensor.hermes_style_filter_status

  - type: button
    name: "Start Cooking"
    tap_action:
      action: call-service
      service: script.start_cooking

  - type: button
    name: "End Cooking"
    tap_action:
      action: call-service
      service: script.end_cooking
```

---

## Tips & Best Practices

### Safety Considerations
- Always include safety timeouts in your automations
- Test automations thoroughly before relying on them
- Keep manual controls accessible
- Monitor error sensors regularly

### Performance Tips
- Use `for` conditions to avoid rapid triggering
- Group related actions in scripts for reusability
- Use templates to reduce automation duplication
- Monitor system logs for issues

### Maintenance
- Review and update automations seasonally
- Check filter reminders regularly
- Test child lock functionality monthly
- Backup automation configurations

---

## Troubleshooting Automations

### Common Issues

**Automation not triggering:**
- Check entity availability in Developer Tools
- Verify trigger conditions are correct
- Review Home Assistant logs for errors

**Delayed execution:**
- Reduce automation complexity
- Check Home Assistant system load
- Review network connectivity

**Unexpected behavior:**
- Enable automation tracing in HA
- Check for conflicting automations
- Verify device firmware is up to date

---

## Need Help?

- **Documentation**: [README.md](README.md)
- **Troubleshooting**: See README Troubleshooting section
- **Issues**: [GitHub Issues](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions)

---

*Generated for KKT Kolbe Home Assistant Integration v2.2.0*
