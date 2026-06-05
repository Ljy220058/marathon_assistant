# Strava Uploads API

Source URL: https://developers.strava.com/docs/uploads/
Accessed at: 2026-05-30

Uploading to Strava is an asynchronous process. A file is uploaded using a multipart/form-data POST request which performs initial checks on the data and enqueues the file for processing. The activity will not appear in other API requests until it has finished processing successfully.

Processing status may be checked by polling Strava. A one-second or longer polling interval is recommended. The mean processing time is currently under 2 seconds. Once processing is complete, Strava will respond to polling requests with the activity’s ID. The activity might be fully processed even if segment processing is not complete.

Errors can occur during the submission or processing steps and may be due to malformed activity data or duplicate data submission.


## Supported File Types

Strava supports FIT, TCX, GPX, and JSON (limited) file types as described below. New file types are not on the road map. Developers are encouraged to use one of these types as it will also maximize compatibility with other fitness applications.

All files are required to include a time with each trackpoint or record, as defined by the file format. Information such as lat/lng, elevation, heartrate, etc. is optional.

An exception to this rule applies to FIT or JSON files that contain sets. See their respective sections for more details.

If you feel your file is compatible with the standards but is still not uploading to Strava, please verify that it works with other fitness applications before contacting support.


### FIT - Flexible and Interoperable Data Transfer

Strava strives to comply with the FIT Activity File (FIT_FILE_TYPE = 4) spec as defined in the official FIT SDK .

There are many attributes defined by FIT. Below is an overview of the ones used by Strava.

For WeightTraining, HighIntensityIntervalTraining, Workout, and Crossfit activities, we also support Set Messages. We support all FIT exercises as defined by the FIT SDK. Some exercise mappings may map to a more general type in Strava. If exercises are not appearing as expected, please reach out to our team at developers@strava.com. For FIT files that contain set messages, they do not require record messages with timestamps. Instead, the file must include timestamp in the activity message and total_elapsed_time in the session message, which are used to determine the start and end time of the activity.

Activity type is detected from session.sport & session.sub_sport .

In order to provide a registered manufacturer & unique product, the manufacturer ID must be assigned to your company by ( ANT+ ).


### TCX - Training Center Database XML

The TCX format was developed by Garmin as part of their Training Center software. For Strava users, an advantage is its ability to include power information. However, it does not support temperature. Strava supports version 2 as defined by Garmin ( schema file ).

The base version of TCX does not allow for the inclusion of run cadence or power. As a result, TCX has been extended. From the extensions available, Strava extracts from the <Trackpoint> tag:

- runcadence as cadence
Strava reads TCX Courses and only uses the <Track> , <TotalTimeSeconds> <DistanceMeters> , and <Calories> from the <Lap> tag. All other aggregated information is ignored.

Activity type is detected from <Activity Sport="*"> where ‘biking’, ‘running’, ‘hiking’, ‘walking’ and ‘swimming’ are mapped to their respective activity types. No other types are currently supported.

A reference TCX file can be obtained for any of your own activities from the Strava website. Visit here , first replacing :id with the ID of one of your own activities.


### GPX - GPS Exchange Format

GPX is a widely used XML format for geospatial data. Strava follows version 1.1 as defined by Topografix .

The base version of GPX does not allow for the inclusion of heartrate, cadence, distance or temperature data. As a result, extensions to GPX were created and Strava supports the two most popular plus a general format. The extensions extend the tag to include extra attributes with each datapoint.

Garmin’s Track Point Extension v1 From the extensions available, Strava extracts:

- atemp as temperature
Cluetrust GPX extension From the extensions available, Strava extracts:

- distance as distance
Strava also detects general tags placed in the <extensions> tag of each tag. Strava extracts:

- heartrate as heartrate
Some smaller organizations have created their own undefined extensions to GPX. Adding support for these extensions is not on the roadmap and developers are encouraged to use one of those above as it will also maximize compatibility with other fitness applications.


### JSON - Strength Training (Limited)

Strava supports a JSON file format for WeightTraining, HighIntensityIntervalTraining, Workout, and Crossfit activities only. This format allows developers to upload structured strength training data including individual sets and optional time-series streams.

Each set object represents a single exercise set.

The streams object is optional. If provided, the time array is required and all other stream arrays must be the same length as time .

The following exercise_type values are supported:

Bench Press: BENCH_PRESS_GENERIC, BARBELL_BENCH_PRESS, DUMBBELL_BENCH_PRESS, INCLINE_DUMBBELL_BENCH_PRESS, INCLINE_BARBELL_BENCH_PRESS, CLOSE_GRIP_BARBELL_BENCH_PRESS, WIDE_GRIP_BARBELL_BENCH_PRESS, SINGLE_ARM_CABLE_CHEST_PRESS, DECLINE_DUMBBELL_BENCH_PRESS, NEUTRAL_GRIP_DUMBBELL_BENCH_PRESS, NEUTRAL_GRIP_DUMBBELL_INCLINE_BENCH_PRESS, FLOOR_BENCH_PRESS, CHEST_PRESS, DUMBBELL_FLOOR_PRESS, BARBELL_FEET_UP_BENCH_PRESS, MACHINE_DECLINE_BENCH_PRESS, SMITH_MACHINE_INCLINE_BENCH_PRESS, MACHINE_INCLINE_CHEST_PRESS, MACHINE_CHEST_PRESS, MACHINE_ISOLATERAL_CHEST_PRESS, DUMBBELL_SQUEEZE_PRESS, PLATE_PRESS, SVEND_PRESS_PLATE_SQUEEZE

Calf Raise: CALF_RAISE_GENERIC, STANDING_CALF_RAISE, SEATED_CALF_RAISE, SINGLE_LEG_STANDING_CALF_RAISE, WALKING_CALF_RAISES, BENT_KNEE_CALF_RAISE, DOUBLE_LEG_CALF_RAISE_ON_STEP, FLOATING_HEEL_DROP, MACHINE_CALF_EXTENSION, MACHINE_CALF_PRESS

Cardio: CARDIO_GENERIC, JUMP_ROPE, JUMPING_JACKS, CARDIO_CORE_CRAWL, SKI_MOGULS, BATTLE_ROPES, ROWING_MACHINE, SLED_PUSH, HIGH_KNEES

Carry: CARRY_GENERIC, BAR_HOLDS, FARMERS_WALK, OVERHEAD_CARRY, FARMERS_CARRY, DEAD_HANG, SUITCASE_CARRY

Chop: CHOP_GENERIC, CROSS_CHOP_TO_KNEE, HALF_KNEELING_ROTATIONAL_CHOP, STANDING_ROTATIONAL_CHOP, CABLE_WOODCHOP, DOWN_TO_UP_CABLE_TWIST, UP_TO_DOWN_CABLE_TWIST

Core: CORE_GENERIC, SWIMMING, LOWER_LIFT, RUSSIAN_TWIST, BARBELL_ROLLOUT, SIDE_BEND, HALF_TURKISH_GET_UP, MODIFIED_FRONT_LEVER, GHD_BACK_EXTENSIONS, OVERHEAD_WALK, CAT_COW, THE_HUNDRED, CABLE_CORE_PRESS, CABLE_SIDE_BEND, KETTLEBELL_WINDMILL, SWISS_BALL_JACKKNIFE, BICYCLE_CRUNCH, HOLLOW_ROCK, LEG_EXTENSIONS, REVERSE_CRUNCH, HANGING_KNEE_RAISE, CABLE_CRUNCH, CRUNCH, TURKISH_GET_UP, DEADBUG, STRAIGHT_LEG_RAISE, FIGURE_OF_8S, SWISSBALL_STIR_POT, CRUNCH_AND_PRESS, DIAGONAL_TOE_TAP, TRAVELLING_PRESS_UP_WALK_OUT, TOE_SCRUNCHES, BIRD_DOG, HIP_DROP, BANDED_DEADBUG, STANDING_MARCH, BICYCLE_CRUNCH_RAISED_LEGS, DECLINE_CRUNCH, WEIGHTED_DECLINE_CRUNCH, DRAGON_FLAG, ELBOW_TO_KNEE, HEEL_TAPS, LYING_KNEE_RAISE, OBLIQUE_CRUNCH, FRONT_LEVER_HOLD, FRONT_LEVER_RAISE, PALLOF_PRESS, AB_WHEEL_ROLLOUT, AB_CRUNCH_MACHINE, MEDICINE_BALL_CRUNCH

Curl: CURL_GENERIC, DUMBBELL_HAMMER_CURL, BARBELL_BICEPS_CURL, CABLE_BICEPS_CURL, BARBELL_REVERSE_WRIST_CURL, BARBELL_WRIST_CURL, CABLE_HAMMER_CURL, INCLINE_DUMBBELL_BICEPS_CURL, STANDING_DUMBBELL_BICEPS_CURL, EZ_BAR_PREACHER_CURL, STANDING_EZ_BAR_BICEPS_CURL, KETTLEBELL_BICEPS_CURL, DUMBBELL_REVERSE_WRIST_CURL, BANDED_HAMSTRING_CURL, DUMBBELL_WRIST_CURL, TWENTY_ONES_BICEP_CURL, MACHINE_BICEP_CURL, SUSPENSION_BICEP_CURL, CONCENTRATION_CURL, CROSS_BODY_HAMMER_CURL, DRAG_CURL, CABLE_OVERHEAD_CURL, DUMBBELL_PINWHEEL_CURL, PLATE_CURL, BARBELL_REVERSE_CURL, ROPE_CABLE_CURL, DUMBBELL_ZOTTMAN_CURL, BARBELL_BEHIND_THE_BACK_BICEP_WRIST_CURL, SEATED_PALMS_UP_WRIST_CURL, BARBELL_SEATED_WRIST_EXTENSION, WRIST_ROLLER, PREACHER_CURL_MACHINE, SPIDER_CURL, CABLE_CURL, REVERSE_CABLE_CURLS

Deadlift: DEADLIFT_GENERIC, BARBELL_DEADLIFT, DUMBBELL_DEADLIFT, BARBELL_STRAIGHT_LEG_DEADLIFT, SUMO_DEADLIFT, RACK_PULL, TRAP_BAR_DEADLIFT, SINGLE_LEG_STRAIGHT_LEG_DEADLIFT, STRAIGHT_LEG_DEADLIFT, KB_STRAIGHT_LEG_DEADLIFT, SL_DB_RDL_KNEE_DRIVE, CONVENTIONAL_DEADLIFTS, DUMBBELL_ROMANIAN_DEADLIFTS, ROMANIAN_DEADLIFTS, SINGLE_LEG_ROMANIAN_DEADLIFTS, STAGGERED_RDLS, CABLE_RDL, BARBELL_ROMANIAN_DEADLIFT

Flye: FLYE_GENERIC, DUMBBELL_FLYE, CABLE_CROSSOVER, INCLINE_DUMBBELL_FLYE, KETTLEBELL_FLYE, DUMBBELL_CHEST_FLY, BAND_CHEST_FLY, SUSPENSION_CHEST_FLY, PEC_DECK_BUTTERFLY, LOW_CABLE_FLY_CROSSOVERS, INCLINE_REVERSE_FLY, INCLINE_CABLE_FLY, DUMBBELL_REAR_DELT_FLY

Hip Raise: HIP_RAISE_GENERIC, BARBELL_HIP_THRUST_ON_FLOOR, CLAMS, SINGLE_LEG_HIP_RAISE, BARBELL_HIP_THRUST_WITH_BENCH, HIP_RAISE, ABDUCTOR_SIDE_LEG_RAISE, STEP_DOWN, RAISED_LEG_HIP_THRUST, SINGLE_LEG_GLUTE_BRIDGE, STAGGERED_HIP_THRUST, BARBELL_HIP_THRUST, GLUTE_BRIDGE, LATERAL_WALK, THRUSTER, HIP_THRUST, SL_ISO_HAMSTRING_HOLD, GLUTE_BRIDGE_HAM_WALKOUT, BARBELL_PARTIAL_GLUTE_BRIDGE, DUMBBELL_SINGLE_LEG_HIP_THRUST, MACHINE_GLUTE_KICKBACK, GLUTE_KICKBACK_ON_FLOOR, DUMBBELL_HIP_THRUST, PLATE_HIP_THRUST, BARBELL_SINGLE_LEG_HIP_THRUST

Hip Stability: HIP_STABILITY_GENERIC, FIRE_HYDRANT_KICKS, PRONE_HIP_INTERNAL_ROTATION, QUADRUPED, SIDE_LYING_LEG_RAISE, STANDING_ADDUCTION, STANDING_HIP_ABDUCTION, LATERAL_WALKS_WITH_BAND_AT_ANKLES, FIRE_HYDRANTS, MACHINE_HIP_ABDUCTION, MACHINE_HIP_ADDUCTION

Hip Swing: HIP_SWING_GENERIC, KETTLEBELL_SWING, STEP_OUT_SWING, SINGLE_ARM_DUMBBELL_SWING, SINGLE_ARM_KETTLEBELL_SWING

Hyperextension: HYPEREXTENSION_GENERIC, BACK_EXTENSION_WITH_OPPOSITE_ARM_AND_LEG_REACH, BACK_EXTENSION, SUPERMAN_FROM_FLOOR, MACHINE_BACK_EXTENSION, REVERSE_HYPER

Lateral Raise: LATERAL_RAISE_GENERIC, FRONT_RAISE, BAR_MUSCLE_UP, MUSCLE_UP, WALL_SLIDE, FORTY_FIVE_DEGREE_CABLE_EXTERNAL_ROTATION, RING_DIP, RING_MUSCLE_UP, ROPE_CLIMB, BAND_PULLAPARTS, OVERHEAD_PLATE_RAISE, PLATE_FRONT_RAISE, CABLE_REAR_DELT_REVERSE_FLY, MACHINE_REAR_DELT_REVERSE_FLY, KETTLEBELL_AROUND_THE_WORLD, KETTLEBELL_HALO, HANDSTAND_HOLD, CABLE_LATERAL_RAISE, CABLE_REAR_DELT_FLY

Leg Curl: LEG_CURL_GENERIC, GOOD_MORNING, SLIDING_LEG_CURL, NORDIC_CURL, GLUTE_HAM_RAISE, MACHINE_LEG_CURL_SEATED, CABLE_GOOD_MORNING, STANDING_LEG_CURL

Leg Raise: LEG_RAISE_GENERIC, HANGING_LEG_RAISE, LYING_STRAIGHT_LEG_RAISE, KNEE_DRIVE, STEP_UPS, LEG_RAISE_PARALLEL_BARS

Lunge: LUNGE_GENERIC, WALKING_LUNGE, BARBELL_REVERSE_LUNGE, BARBELL_BULGARIAN_SPLIT_SQUAT, BARBELL_LUNGE, SIDE_LUNGE, OVERHEAD_LUNGE, REVERSE_LUNGE, STATIC_LUNGE, BARBELL_OVERHEAD_LUNGE, REAR_LEG_RAISED_LUNGE, FRONT_LEG_RAISED_LUNGE, BANDED_SIDE_LUNGE, LUNGE_HOLD_CALF_RAISE, LUNGE_AND_PRESS, DUMBBELL_WALKING_LUNGES, LATERAL_LUNGE, SMITH_MACHINE_LUNGE, BARBELL_SPLIT_SQUAT, SKATER_LUNGE

Olympic Lift: OLYMPIC_LIFT_GENERIC, CLEAN, BARBELL_HANG_POWER_CLEAN, BARBELL_HANG_SQUAT_CLEAN, BARBELL_POWER_CLEAN, BARBELL_POWER_SNATCH, BARBELL_SQUAT_CLEAN, BARBELL_HANG_POWER_SNATCH, BARBELL_HANG_PULL, BARBELL_HIGH_PULL, BARBELL_SNATCH, BARBELL_SPLIT_JERK, CLEAN_AND_JERK, PUSH_JERK, SINGLE_ARM_HANG_SNATCH, SPLIT_JERK, SQUAT_CLEAN_AND_JERK, DUMBBELL_CLEAN, DUMBBELL_HANG_PULL, ONE_HAND_DUMBBELL_SPLIT_SNATCH, SINGLE_ARM_DUMBBELL_SNATCH, SINGLE_ARM_KETTLEBELL_SNATCH, SINGLE_ARM_CLEAN_AND_PRESS, SINGLE_ARM_SNATCH, DOUBLE_ARM_CLEAN_AND_PRESS, DOUBLE_ARM_SNATCH, KETTLEBELL_CLEAN

Plank: PLANK_GENERIC, MOUNTAIN_CLIMBER, PLANK_WITH_ARM_RAISE, CROSS_BODY_MOUNTAIN_CLIMBER, BEAR_CRAWL, SIDE_PLANK, SIDEPLANK_HIP_FLEXORS, SIDE_PLANK_LEG_RAISE, SL_COPENHAGEN_PLANK, LL_COPENHAGEN_PLANK, PLANK_TWIST, PLANK_PULL_THROUGH, PLANK_ON_SWISSBALL, SWISSBALL_HIGH_PLANK, PLANK_HOLD, SIDE_PLANK_HOLD

Plyo: PLYO_GENERIC, BODY_WEIGHT_JUMP_SQUAT, ALTERNATING_JUMP_LUNGE, CROSS_KNEE_STRIKE, DEPTH_JUMP, LATERAL_LEAP_AND_HOP, MEDICINE_BALL_OVERHEAD_THROWS, MEDICINE_BALL_SLAM, BOX_JUMP, FULL_STAR_JUMPS, POGO_JUMPS, HURDLE_HOPS, SL_BOX_JUMP, DL_SKIPPING, BOX_JUMP_DOWN_TUCK_JUMP, SEATED_START_BOX_JUMP, BALL_SLAMS, LATERAL_BOX_JUMP, BOX_JUMP_DOWN, BROAD_JUMP, BOX_JUMP_OVER, LATERAL_MEDICINE_BALL_SLAM

Pull Up: PULL_UP_GENERIC, LAT_PULLDOWN, CLOSE_GRIP_CHIN_UP, STRAIGHT_ARM_PULLDOWN, ASSISTED_CHIN_UP, WEIGHTED_CHIN_UP, NEGATIVE_PULL_UP, RING_PULL_UP, GIRONDA_STERNUM_PULL_UP, WIDE_PULL_UP, CABLE_LAT_PULLDOWN_CLOSE_GRIP, SINGLE_ARM_LAT_PULLDOWN, UNDERHAND_LAT_PULLDOWN, NEUTRAL_GRIP_LAT_PULLDOWN, NEUTRAL_GRIP_PULL_UP

Push Up: PUSH_UP_GENERIC, DECLINE_PUSH_UP, DIAMOND_PUSH_UP, HANDSTAND_PUSH_UP, INCLINE_PUSH_UP, ONE_ARM_PUSH_UP, MILITARY_PRESS_UP, MODIFIED_PUSH_UP, PLANK_TO_PUSH_UP, CLAP_PUSH_UPS

Row: ROW_GENERIC, SEATED_CABLE_ROW, DUMBBELL_ROW, FACE_PULL, RENEGADE_ROW, REVERSE_GRIP_BARBELL_ROW, T_BAR_ROW, KETTLEBELL_ROW, ROLL_DOWN, BENT_OVER_ROW, SWISSBALL_BACK_EXTENSION, SUPERMAN, BENT_OVER_BARBELL_ROW, BENT_OVER_DUMBBELL_ROW, MACHINE_ISOLATERAL_HIGH_ROW, LANDMINE_ROW, SUSPENSION_LOW_ROW, MACHINE_SEATED_ROW, DUMBBELL_PULLOVER, MACHINE_PULLOVER, MACHINE_CHEST_SUPPORTED_ROW, SEAL_ROW, MEADOWS_ROW, SMITH_MACHINE_ROW, CHEST_SUPPORTED_ROW

Shoulder Press: SHOULDER_PRESS_GENERIC, OVERHEAD_BARBELL_PRESS, BARBELL_PUSH_PRESS, ARNOLD_PRESS, OVERHEAD_DUMBBELL_PRESS, STANDING_SINGLE_ARM_SHOULDER_PRESS, FLOOR_SEATED_SINGLE_ARM_SHOULDER_PRESS, STANDING_DOUBLE_ARM_SHOULDER_PRESS, FLOOR_SEATED_DOUBLE_ARM_SHOULDER_PRESS, PUSH_PRESS, STANDING_BARBELL_PRESS, SEATED_BARBELL_PRESS, BARBELL_BEHIND_THE_HEAD_SHOULDER_PRESS, PRESS_UP_POSITION_SHOULDER_TAP, SHOULDER_FOCUSED_PRESS_UP, DUMBBELL_PUSH_PRESS, SMITH_MACHINE_OVERHEAD_PRESS, MACHINE_SEATED_SHOULDER_PRESS, LANDMINE_SQUAT_AND_PRESS, SEATED_DUMBBELL_SHOULDER_PRESS

Shoulder Stability: SHOULDER_STABILITY_GENERIC, FLOOR_I_RAISE, FLOOR_T_RAISE, FLOOR_Y_RAISE, INCLINE_L_RAISE, INCLINE_W_RAISE, CABLE_PULL_APART

Shrug: SHRUG_GENERIC, BARBELL_SHRUG, BARBELL_UPRIGHT_ROW, SCAPULAR_RETRACTION, SERRATUS_SHRUG, JUMP_SHRUG, CABLE_UPRIGHT_ROW

Sit Up: SIT_UP_GENERIC, V_UP, THE_TEASER, PRESS_UP_POSITION_DIAGONAL_TOE_TAP, PRESS_UP_POSITION_WITH_SINGLE_ARM_EXTENSION, PRESS_UP_POSITION_WALK_OUT

Squat: SQUAT_GENERIC, BARBELL_BACK_SQUAT, GOBLET_SQUAT, LEG_PRESS, BARBELL_FRONT_SQUAT, BARBELL_SQUAT_SNATCH, BARBELL_STEP_UP, OVERHEAD_SQUAT, STEP_UP, PISTOL_SQUAT, SUMO_SQUAT, THRUSTERS, ZERCHER_SQUAT, KETTLEBELL_SQUAT, BARBELL_SQUAT, LOPSIDED_SQUAT, KB_FRONT_RACKED_SQUAT, STEP_UP_AND_KNEE_DRIVE, QUAD, SQUAT_TO_CALF_RAISE, DUMBBELL_BULGARIAN_SPLIT_SQUATS, DUMBBELL_GOBLET_SQUATS, GOBLET_SQUATS, WALL_SIT, BARBELL_BOX_SQUAT, ASSISTED_PISTOL_SQUATS, MACHINE_LEG_PRESS, MACHINE_HACK_SQUAT, MACHINE_SINGLE_LEG_PRESS, BELT_SQUAT, SMITH_MACHINE_SQUAT, MACHINE_LEG_EXTENSION, AIR_SQUAT, COSSACK_SQUAT

Total Body: TOTAL_BODY_GENERIC, BURPEE, SQUAT_THRUSTS, STANDING_T_ROTATION_BALANCE, BURPEE_OVER_THE_BAR

Triceps Extension: TRICEPS_EXTENSION_GENERIC, TRICEPS_PRESSDOWN, SKULL_CRUSHER, BENCH_DIP, DUMBBELL_KICKBACK, BODY_WEIGHT_DIP, OVERHEAD_DUMBBELL_TRICEPS_EXTENSION, SEATED_BARBELL_OVERHEAD_TRICEPS_EXTENSION, TRICEP_DIP, CABLE_OVERHEAD_TRICEPS_EXTENSION, FLOOR_TRICEPS_DIP, CHEST_DIP, ASSISTED_CHEST_DIP, WEIGHTED_CHEST_DIP, SEATED_DIP_MACHINE, SEATED_TRICEPS_PRESS, DUMBBELL_SINGLE_ARM_TRICEP_EXTENSION, CABLE_SINGLE_ARM_TRICEPS_PUSHDOWN, DUMBBELL_SKULLCRUSHER, DUMBBELL_WIDEELBOW_TRICEPS_PRESS, MACHINE_TRICEP_EXTENSION, CABLE_TRICEPS_PUSHDOWN

Warm Up: WARM_UP_GENERIC, OPPOSITE_ARM_AND_LEG_BALANCE, WALKOUT, QUADRUPED_ROCKING, NECK_TILTS, ANKLE_CIRCLES, ARM_CIRCLES, FORWARD_AND_BACKWARD_LEG_SWINGS, LATERAL_DUCK_UNDER, REACH_ROLL_AND_LIFT, SLEEPER_STRETCH, THORACIC_ROTATION, WALKING_HIGH_KICKS, WALKING_HIGH_KNEES, WALKING_KNEE_HUGS, INVERTED_HAMSTRING_STRETCH, STRETCH, HAMSTRING_WALKOUT, HEEL_WALKS, TOE_WALKS, SIDE_LEG_SWINGS


## Device and Elevation Data

For devices with a barometric altimeter the elevation data is taken as is from the file, unless it is clearly inaccurate. Otherwise it is recomputed using the provided lat/lng points and an elevation database. More information

Device type is detected in all file types from standard ‘creator’ tags in TCX/GPX files, and manufacturer/product ID values in FIT files. These values are then matched to a list of known devices. In some cases the name of the device will be displayed along with the activity details on strava.com .

A generic “with barometer” device is provided to force the system to use the elevation data from TCX and GPX file types. One only needs to add “with barometer” to the end of the creator name. For example, a TCX file would include something like: <Creator> <Name>My Awesome Device with barometer</Name> </Creator>

and a GPX file should have an updated creator like:

For total elevation gain, the value is read directly from FIT file headers if the device includes a barometric altimeter. Otherwise, elevation gain will be computed from the elevation data and may be different than reported on the device. Note that to compute elevation gain noise must be removed from the elevation data and different algorithms/sites will produce different results. More information

Strava maintains a database of devices for display on activities uploaded from them. If you manufacture a device and would like it mapped on Strava, the uploaded files simply need to follow one of the following requirements:

- TCX: A unique device name in <Creator><Name>UNIQUE_DEVICE_NAME</Name></Creator>
- FIT: A registered manufacturer & unique product , the manufacturer ID must be assigned to your company by ant+
- GPX: A unique device name in <gpx version="1.1" creator="UNIQUE_DEVICE_NAME">
Request a device mapping by submitting this form which requires the following information:

- A compliant sample file for each type of file you support
- Exact name of your company
- Exact name of device
- URI to device product page
- Official contact & support info
- Existence of a barometric altimeter in the device

## How to Upload an Activity

Requires activity:write permissions, as requested during the authorization process.

Posting a file for upload will enqueue it for processing. Initial checks will be done for malformed data and duplicates.

POST https://www.strava.com/api/v3/uploads

For file, the @ symbol means to use the content of the file at the file path we specify. Otherwise, we are just giving it a string that’s the file name, not the content.

Note that in the future the ID will be a 64-bit value, too large to be represented in 32 bits, or as a JavaScript number. Please ensure you can handle 64-bit integers, or use the id_str field.

This object will return a code and an English language status. On success, a 201 Created will be accompanied by a status of success . This indicates that the activity has been successfully accepted, but is still processing. On error, the 400 Bad Request will be accompanied by a status describing the error, potentially containing HTML.

A successful upload will return a response with an upload ID. You may use this ID to poll the status of your upload. Strava recommends polling no more than once a second. The mean processing time is under 2 seconds.

GET https://www.strava.com/api/v3/uploads/:id

You can determine if there was an error during upload by checking the error attribute for null. At this time error and status messages returned as part of the Upload object are human readable English. They may also include escaped HTML.
