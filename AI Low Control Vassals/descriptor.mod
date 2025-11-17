############################################################
# Mod: AI Low Control Vassals
# Purpose: Encourages AI overlords to manage sprawling realms
#          by releasing new vassals from very high-autonomy
#          provinces and ceding high-autonomy border provinces
#          to their smallest existing vassals.
# Files:
#  - scripted_triggers: Logic gates for release/cede choices
#  - scripted_effects: Province cede + government sync
#  - events: Daily AI checks to release or cede
# Gameplay Impact:
#  - Keeps large AI nations from sitting on inefficient land
#  - Creates smaller, thematically appropriate vassals
#  - Promotes dynamic political fragmentation
# Version metadata below kept minimal; extend tags={} if needed.
############################################################
version="1"
tags={
}
name="AI Low Control Vassals"
supported_version="v1.37.5.0"
