# Pirate Federations Mod

## Overview
This mod adds the ability for Pirate Republics to form federations with other island nations, expanding the pirate gameplay experience in Europa Universalis IV.

## Features

### Pirate Federation Subject Type
- A new subject type specifically for pirate federations
- Federation members maintain high autonomy and can act independently
- Members provide naval forcelimit and sailors to the federation leader
- Lower liberty desire than traditional vassals (pirates help each other willingly)
- **Auto-expulsion:** Members who change away from Pirate Republic government are automatically expelled with notification
- Both leader and members gain bonuses:
  - **Leader benefits:** +5% Naval Forcelimit, +5% Capture Ship Chance, +10% Privateer Efficiency per member
  - **Member benefits:** +10% Privateer Efficiency, +5% Naval Morale, +5% Ship Trade Power

### Diplomatic Invitation
- **NEW:** Peacefully invite island nations to join your federation via diplomatic action
- **Requirements:**
  - Your country must be a Pirate Republic
  - Target must be entirely on islands (all provinces)
  - Target cannot be a subject or already a Pirate Republic
  - Target must not be at war
- AI acceptance based on opinion, your naval strength, and their security situation
- Converts them to Pirate Republic and creates federation membership

### Invitation CB (Forced)
- Use military force to compel island nations to join your federation
- **Requirements:**
  - Your country must be a Pirate Republic
  - Target must be **entirely on islands** (all provinces must be on islands)
  - Target cannot already be a Pirate Republic or federation member
  - Target must be a neighbor or within naval range
- Lower aggressive expansion than vassalization (0.5x modifier)
- War goal: Force the enemy to become a Pirate Republic and join your federation

### Liberation CB
- **NEW:** Liberate island provinces and create pirate havens
- Target nations that control islands (doesn't need to be entirely islands)
- Use the "Release as Pirate Republic" peace option to create new pirate nations
- Very low aggressive expansion (0.3x modifier)
- Perfect for liberating: Corsica, Sardinia, Cyprus, Crete, Corfu, Rhodes, Caribbean islands, etc.
- Released nations automatically join your federation as Pirate Republics

## Gameplay Tips
1. **Diplomatic Approach:** Try peaceful invitation first - it's cheaper and doesn't cost AE
2. **Forced Invitation:** Use the invitation CB on small island nations (Cyprus, Malta, etc.)
3. **Liberation Strategy:** Use the liberation CB against larger nations to carve out pirate havens from their islands
4. **Building a Network:** Chain liberation wars to create a network of pirate havens
5. **Ideal Targets:** 
   - **Mediterranean:** Corsica, Sardinia, Cyprus, Crete, Malta, Corfu, Rhodes
   - **Caribbean:** All the small island nations
   - **Southeast Asia:** Indonesian and Philippine islands
   - **Atlantic:** Azores, Madeira, Canary Islands
   - **Any island provinces** with releasable nations

## Compatibility
- Version: 1.37.*.*
- Compatible with most other mods
- Should work alongside mods that modify government reforms or diplomacy

## Installation
1. Place the mod folder in your EU4 mod directory
2. Enable the mod in the EU4 launcher
3. Start a new game or load an existing save

## Credits
Created for enhanced pirate gameplay experience.

## Changelog
### Version 1.2
- **Auto-expulsion:** Federation members who stop being Pirate Republics are automatically expelled
- Both the expelled nation and the federation leader receive notifications
- Checked yearly to maintain federation integrity

### Version 1.1
- Changed invitation CB to only work on nations **entirely on islands**
- Added diplomatic action to peacefully invite island nations
- Added new Liberation CB for releasing island provinces
- Liberation CB works on any nation with islands (doesn't need to be entirely islands)
- Updated all descriptions and tooltips

### Version 1.0
- Initial release
- Added Pirate Federation subject type
- Added Invitation CB
- Added Release as Pirate Republic peace option
