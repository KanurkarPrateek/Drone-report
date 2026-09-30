"""Asset profiles: what to look for, how to label it, and how to fix it.

Everything an inspector would want to review lives here. The vision model is told
what to look for from `look_for`; Jev picks a label from `categories`; the report
pulls the standard repair procedure from `playbook`. Edit this file to add an
asset type (wind turbines, transmission towers, roofs, ...).
"""

SEVERITY_LEVELS = [
    "Cosmetic: no functional impact, note for records only.",
    "Minor: early-stage wear; no loss of function; fix at next scheduled maintenance.",
    "Moderate: measurable degradation or loss of output; fix within 30-90 days.",
    "Major: active damage or significant loss of function; fix within 7-30 days.",
    "Critical: active leak, fire, structural failure risk or danger to people or environment; act immediately.",
]
SEVERITY_NAMES = ["Cosmetic", "Minor", "Moderate", "Major", "Critical"]

ACTIONS = {
    "monitor": "No intervention yet. Re-inspect on the next flight and track if it grows.",
    "clean": "Remove dirt, debris, deposits, vegetation or spilled material; no component repair needed.",
    "repair": "Fix the component in place (patch, recoat, re-torque, re-seal, re-route).",
    "replace": "The component is beyond repair and must be swapped out.",
    "isolate_and_shutdown": "Isolate the section and stop operation now because of safety or environmental danger.",
}

ACTION_LABELS = {"monitor": "Monitor", "clean": "Clean", "repair": "Repair", "replace": "Replace",
                 "isolate_and_shutdown": "Shut down"}

PROFILES = {
    "oil_gas": {
        "name": "Oil & Gas Facility",
        "look_for": (
            "pipelines, flowlines, wellheads, pumpjacks, storage tanks, separators, valves, flanges, "
            "pipe supports, secondary containment berms, flare stacks. Look for oil/liquid leaks, dark "
            "stains or pooling on soil, sheens on water, rust and corrosion, peeling coating, damaged "
            "insulation/cladding, dents, cracks, sagging or broken pipe supports, breached or eroded "
            "berms, vegetation growing into equipment, damaged fencing, and abnormal flaring or venting."
        ),
        "categories": {
            "hydrocarbon_leak": "Active or recent release of oil, gas condensate or produced water: wet stains, pooling, drips, sheen, spray.",
            "corrosion": "Rust, scaling, pitting or metal loss on pipe, tank, valve or structural steel.",
            "coating_failure": "Paint or protective coating peeling, blistering, chalking or missing, exposing the base metal.",
            "insulation_damage": "Torn, missing, water-soaked or displaced insulation or cladding (risk of corrosion under insulation).",
            "structural_damage": "Dents, cracks, deformation, sagging lines, broken or missing pipe supports, tank shell buckling.",
            "containment_breach": "Secondary containment berm or bund that is eroded, breached, overtopped or holding liquid.",
            "vegetation_encroachment": "Vegetation growing on or against equipment, the right-of-way or containment.",
            "fire_or_explosion": "Uncontrolled fire, explosion, burning equipment or product, heavy smoke from an incident, or equipment exposed to fire heat.",
            "flare_or_venting_anomaly": "Smoky, unlit, oversized or unexpected flare, or visible venting plume from normal process equipment (not an incident fire).",
            "security_or_access": "Damaged fence or gate, missing signage, unauthorised access or blocked access road.",
            "other": "Any other anomaly that needs an engineer's attention.",
        },
        "playbook": {
            "hydrocarbon_leak": {
                "steps": [
                    "Treat as a potential release: notify the site supervisor and HSE lead immediately.",
                    "Isolate the affected segment (close upstream/downstream block valves) and depressurise if safe.",
                    "Deploy absorbent booms/pads; contain spread to soil or water.",
                    "Locate the source (flange gasket, valve packing, pinhole, fitting) with a ground crew and gas detector.",
                    "Repair: re-torque or replace the gasket, repack the valve, or install an engineered clamp; replace the pipe spool for through-wall corrosion.",
                    "Excavate and dispose of contaminated soil; record volume released for regulatory reporting.",
                ],
                "crew": "Operations + HSE + mechanical/pipefitter crew",
                "references": ["40 CFR Part 112 (SPCC)", "API 570 Piping Inspection Code", "API RP 1160 (pipelines)"],
            },
            "corrosion": {
                "steps": [
                    "Send a ground team to measure remaining wall thickness (UT gauging) at the corroded area.",
                    "Compare against minimum required thickness; calculate remaining life and corrosion rate.",
                    "If above minimum: blast-clean to bare metal and apply a suitable protective coating system.",
                    "If below minimum or pitting is deep: install a sleeve/clamp or replace the pipe section.",
                    "Check cathodic protection readings on buried or tank-bottom sections.",
                ],
                "crew": "Integrity / NDT inspector + coatings contractor",
                "references": ["API 570", "API 571 (damage mechanisms)", "AMPP/NACE SP0169 (cathodic protection)"],
            },
            "coating_failure": {
                "steps": [
                    "Mark the area and check for corrosion underneath (spot UT reading).",
                    "Surface-prepare (power-tool or abrasive blast) to the coating manufacturer's standard.",
                    "Apply primer and topcoat per the site coating specification; record dry film thickness.",
                ],
                "crew": "Coatings contractor",
                "references": ["API 570", "AMPP (NACE/SSPC) surface-prep standards"],
            },
            "insulation_damage": {
                "steps": [
                    "Remove damaged insulation and inspect the pipe for corrosion under insulation (CUI).",
                    "Repair any metal loss found; recoat bare steel.",
                    "Reinstall dry insulation and weather-seal the jacketing seams.",
                ],
                "crew": "Insulation contractor + integrity inspector",
                "references": ["API 570 (CUI inspection)", "API 583 (corrosion under insulation)"],
            },
            "structural_damage": {
                "steps": [
                    "Restrict access below or near the damaged structure until assessed.",
                    "Have a structural or mechanical engineer assess the dent, crack or support failure.",
                    "Install temporary supports if a line is sagging.",
                    "Repair or replace the support, or cut out and replace the damaged pipe or tank section.",
                ],
                "crew": "Structural/mechanical engineer + fabrication crew",
                "references": ["API 570", "API 653 (above-ground storage tanks)"],
            },
            "containment_breach": {
                "steps": [
                    "Check whether the containment currently holds liquid; if so, pump out and test for hydrocarbons.",
                    "Rebuild the eroded or breached berm section with compacted fill or liner patch.",
                    "Confirm the containment volume still meets the required capacity.",
                ],
                "crew": "Civil/earthworks crew + HSE",
                "references": ["40 CFR Part 112 (SPCC secondary containment)"],
            },
            "vegetation_encroachment": {
                "steps": [
                    "Clear vegetation from equipment, containment and the right-of-way.",
                    "Apply the site's approved vegetation-control method; schedule recurring clearing.",
                ],
                "crew": "Site maintenance / ROW contractor",
                "references": ["Site vegetation management plan"],
            },
            "fire_or_explosion": {
                "steps": [
                    "Emergency response first: call emergency services, activate the site emergency plan and set an evacuation or shelter-in-place zone (downwind and around tank cars/vessels).",
                    "Stop the fuel: close isolation valves and shut down pumps feeding the fire if it can be done safely.",
                    "Fight hydrocarbon fires with foam, not water jets; cool nearby tanks, tank cars and vessels with water to prevent them overheating and rupturing.",
                    "Keep responders upwind; monitor air quality in nearby homes and at the site boundary.",
                    "Contain runoff (foam, water and oil) away from drains, ditches and waterways with booms and berms.",
                    "After extinguishment: inspect every exposed or damaged tank for punctures, valve damage and heat damage before moving product; offload to sound tanks.",
                    "Report the incident to the regulators that apply (e.g. National Response Center in the US) and preserve evidence for the investigation.",
                ],
                "crew": "Emergency services + site incident command + HSE + hazmat/spill contractor",
                "references": ["NFPA 30 (flammable and combustible liquids)", "NFPA 11 (foam systems)",
                               "PHMSA Emergency Response Guidebook (ERG)", "40 CFR Part 112 (SPCC)"],
            },
            "flare_or_venting_anomaly": {
                "steps": [
                    "Check the flare pilot, assist gas and knockout drum level with the control room.",
                    "Investigate the upstream process upset that is causing excess flaring or venting.",
                    "Record the event for emissions reporting.",
                ],
                "crew": "Operations / process engineer",
                "references": ["40 CFR Part 60 subpart OOOOa/b (emissions)", "API 521 (flare systems)"],
            },
            "security_or_access": {
                "steps": [
                    "Repair fence or gate damage; replace missing warning signs.",
                    "Clear blocked access routes so emergency vehicles can reach the site.",
                ],
                "crew": "Site maintenance",
                "references": ["Site security plan"],
            },
            "other": {
                "steps": ["Have a qualified engineer review the frame and decide on an inspection or repair."],
                "crew": "Site engineer",
                "references": [],
            },
        },
    },
    "solar": {
        "name": "Solar PV Farm / Rooftop Array",
        "look_for": (
            "PV modules, strings, racking/trackers, combiner boxes, inverters, cabling and the ground around "
            "the array. Look for cracked or shattered glass, broken or missing modules, soiling (dust, bird "
            "droppings, leaves), browning, delamination, snail trails, burn marks, hotspots (if the footage is "
            "thermal, bright cells or modules), shading from vegetation or structures, bent or loose racking, "
            "tilted tracker rows, hanging or damaged cables, water pooling or erosion under the array."
        ),
        "categories": {
            "physical_damage": "Cracked, shattered or punctured glass, broken frame, or burn marks on a module.",
            "hotspot": "Thermal anomaly: a cell, substring or whole module that is much hotter than its neighbours.",
            "soiling": "Dust, bird droppings, leaves, snow or other deposits covering part of the module surface.",
            "shading": "Vegetation, structures or debris casting shadows on modules.",
            "degradation": "Browning/discoloration, delamination, bubbles, snail trails or backsheet damage.",
            "missing_or_displaced_module": "A module that is missing, has slid, or is visibly misaligned in the row.",
            "racking_damage": "Bent, broken, corroded or loose mounting structure, or a tracker row stuck at the wrong angle.",
            "cable_issue": "Hanging, pinched, chewed, exposed or unsupported cables and connectors.",
            "site_condition": "Water pooling, erosion, overgrown vegetation or damaged fencing around the array.",
            "other": "Any other anomaly that needs a technician's attention.",
        },
        "playbook": {
            "physical_damage": {
                "steps": [
                    "Treat the module as a shock hazard: broken glass can expose live parts.",
                    "Isolate the string at the combiner box or inverter before touching it.",
                    "Replace the module with a matching model (same electrical rating); record the serial number for warranty.",
                    "Run an I-V curve or string check after replacement.",
                ],
                "crew": "Qualified PV technician (electrical)",
                "references": ["IEC 62446-1 (testing, documentation, maintenance)", "NFPA 70 / NEC Article 690"],
            },
            "hotspot": {
                "steps": [
                    "Confirm with a closer IR scan under steady irradiance (>600 W/m2) and measure the temperature delta.",
                    "Check for soiling or shading causing it; clean first and re-scan.",
                    "If it persists: test the bypass diodes and junction box; replace the module if a cell is damaged.",
                    "Deltas above ~20 C over neighbours are a fire risk; prioritise those.",
                ],
                "crew": "PV technician with thermal camera",
                "references": ["IEC TS 62446-3 (outdoor infrared thermography)", "IEC 62446-1"],
            },
            "soiling": {
                "steps": [
                    "Clean affected modules with deionised water and a soft brush; no abrasive tools or high pressure.",
                    "Clean in the early morning or evening to avoid thermal shock to hot glass.",
                    "Where bird droppings recur, install bird deterrents; review the cleaning interval.",
                ],
                "crew": "O&M cleaning crew",
                "references": ["Module manufacturer's cleaning guide", "IEC 62446-1"],
            },
            "shading": {
                "steps": [
                    "Trim or remove vegetation casting shade; remove debris from the array.",
                    "If a fixed structure shades the array, evaluate optimisers or re-stringing.",
                ],
                "crew": "Site maintenance",
                "references": ["Site vegetation management plan"],
            },
            "degradation": {
                "steps": [
                    "Document with close-up photos and compare output of the affected string against neighbours.",
                    "Test insulation resistance; delamination can let in moisture and cause ground faults.",
                    "File a warranty claim if within the product/performance warranty; replace modules with safety faults.",
                ],
                "crew": "PV technician + asset manager (warranty)",
                "references": ["IEC 61215 (module design qualification)", "IEC 62446-1"],
            },
            "missing_or_displaced_module": {
                "steps": [
                    "Isolate the string; check for exposed or damaged connectors.",
                    "Re-seat and re-clamp the module to the manufacturer's torque spec, or install a replacement.",
                    "Inspect neighbouring clamps for the same loosening (wind loading).",
                ],
                "crew": "PV technician",
                "references": ["Racking manufacturer's installation manual", "NFPA 70 / NEC Article 690"],
            },
            "racking_damage": {
                "steps": [
                    "Restrict access if the structure is unstable.",
                    "Have the racking checked against the design; replace bent or corroded members and re-torque fasteners.",
                    "For stuck trackers: check the motor, controller and stow position.",
                ],
                "crew": "Mechanical/structural crew + tracker vendor",
                "references": ["Racking/tracker manufacturer's O&M manual"],
            },
            "cable_issue": {
                "steps": [
                    "Isolate the circuit before handling.",
                    "Replace damaged cable or connectors (use the same connector brand; never mix MC4 types).",
                    "Re-secure cables with UV-rated clips off the ground and away from sharp edges; add rodent protection if chewed.",
                ],
                "crew": "Qualified PV electrician",
                "references": ["NFPA 70 / NEC Article 690", "IEC 62446-1"],
            },
            "site_condition": {
                "steps": [
                    "Fix drainage or regrade eroded areas near foundations.",
                    "Cut back vegetation; repair fencing.",
                ],
                "crew": "Civil / site maintenance",
                "references": ["Site O&M plan"],
            },
            "other": {
                "steps": ["Have a qualified technician review the frame and decide on an inspection or repair."],
                "crew": "O&M technician",
                "references": [],
            },
        },
    },
    "building": {
        "name": "Buildings & Civic Property",
        # Buildings aren't "shut down"; the urgent action is keeping people out and making safe.
        "actions": {**ACTIONS, "isolate_and_shutdown": (
            "Keep people out and make the area safe now (evacuate, fence off, placard) because of danger to life or of collapse.")},
        "action_labels": {**ACTION_LABELS, "isolate_and_shutdown": "Keep out / make safe"},
        "look_for": (
            "public and civic buildings, schools, community halls, housing, farm buildings (barns, sheds, silos), "
            "and the ground around them. Look for missing, torn or lifted roofing, holes and collapsed roof sections, "
            "exposed decking or rafters, rusted metal roofs, cladding and silos, collapsed or leaning walls and "
            "structures, missing siding or boarded/broken windows, vines and trees growing on or into buildings, "
            "loose sheet metal and debris that can blow, fallen trees on or near buildings, ponding or blocked "
            "drainage, damaged power poles, lines and water tanks, and open or unsecured derelict buildings."
        ),
        "categories": {
            "roof_damage": "Missing, torn, lifted or holed roofing; collapsed roof sections; exposed decking, rafters or trusses.",
            "structural_damage": "Collapsed, leaning or bowed walls, frames, silos or towers; failed framing; major cracks.",
            "corrosion": "Rusted metal roofing, cladding, silos, tanks, frames or fasteners.",
            "envelope_damage": "Missing or damaged siding and cladding, broken or missing windows and doors, open walls.",
            "vegetation_overgrowth": "Vines, shrubs or trees growing on, against or into a structure or its roof.",
            "debris_and_loose_material": "Scattered debris, loose sheet metal, fallen trees or objects that can blow, fall or block access.",
            "drainage_and_water": "Ponding on roofs, blocked gutters or drains, erosion, visible water ingress.",
            "utilities_damage": "Damaged or leaning power poles and lines, damaged water tanks, solar arrays or HVAC on buildings.",
            "security_and_access": "Open or unsecured derelict buildings, broken fences, blocked access roads.",
            "other": "Any other anomaly that needs a surveyor's attention.",
        },
        "playbook": {
            "roof_damage": {
                "steps": [
                    "Keep people out of rooms under the damaged roof until an engineer or building official has checked it.",
                    "Make it weather-tight: cover openings with secured tarps or temporary sheeting (fixed to the structure, not weighed down loosely).",
                    "Have a structural engineer check rafters, trusses and connections under the damaged area before repair.",
                    "Replace damaged decking and roofing; upgrade fixings to current wind-load requirements.",
                    "Roof work needs fall protection (harness, anchors or edge protection).",
                ],
                "crew": "Roofing contractor + structural engineer",
                "references": ["International Existing Building Code (IEBC)", "ASCE 7 (wind loads)", "OSHA 29 CFR 1926.501 (fall protection)"],
            },
            "structural_damage": {
                "steps": [
                    "Cordon off a fall zone around the structure (at least its height) and post it as unsafe.",
                    "Get a structural engineer's rapid safety evaluation (inspected / restricted use / unsafe placard).",
                    "Shore or brace if the structure is to be saved; otherwise plan a controlled demolition.",
                    "Do not let anyone climb or enter until the engineer clears it.",
                ],
                "crew": "Structural engineer + building official; demolition or shoring contractor",
                "references": ["ATC-45 (safety evaluation after windstorms and floods)", "FEMA P-2055 (post-disaster building safety evaluation)", "IEBC"],
            },
            "corrosion": {
                "steps": [
                    "Check how much metal is left: probe rusted areas, look for holes and failed fasteners.",
                    "Surface rust: wire-brush, prime and recoat. Holes or thinned sheets: replace the sheets or panels.",
                    "Replace corroded fasteners and flashing so sheets can't lift in wind.",
                ],
                "crew": "Roofing / metal cladding contractor",
                "references": ["Manufacturer's coating and fastening specs", "International Property Maintenance Code (IPMC)"],
            },
            "envelope_damage": {
                "steps": [
                    "Board up broken windows and doors and cover open walls to keep weather and trespassers out.",
                    "Check framing behind missing cladding for water damage and rot.",
                    "Replace cladding, windows and doors; seal joints.",
                ],
                "crew": "General contractor",
                "references": ["IPMC", "IEBC"],
            },
            "vegetation_overgrowth": {
                "steps": [
                    "Cut vines at the base and let them die back before pulling them off, so they don't tear cladding or mortar.",
                    "Remove trees and shrubs growing against or into the structure, including roots near foundations.",
                    "Inspect the surfaces underneath for damage and moisture.",
                ],
                "crew": "Grounds / arborist crew",
                "references": ["IPMC (exterior property and structure)"],
            },
            "debris_and_loose_material": {
                "steps": [
                    "Secure or remove loose sheet metal and debris that wind can pick up.",
                    "Clear debris from access routes, drains and around buildings.",
                    "Separate hazardous debris (asbestos-cement sheets, treated wood, chemicals) for proper disposal.",
                ],
                "crew": "Debris removal crew",
                "references": ["FEMA Public Assistance debris guidance", "EPA asbestos (NESHAP) rules for demolition debris"],
            },
            "drainage_and_water": {
                "steps": [
                    "Clear blocked gutters, downpipes and roof drains.",
                    "Find and fix the cause of ponding or water ingress; dry out affected areas to prevent mould.",
                ],
                "crew": "Maintenance crew / roofer",
                "references": ["IPMC", "International Plumbing Code (roof drainage)"],
            },
            "utilities_damage": {
                "steps": [
                    "Treat all downed or leaning lines as live; keep people away and call the utility.",
                    "Have the utility or a licensed electrician make safe and restore service.",
                    "Inspect water tanks for shell, roof and foundation damage before refilling.",
                ],
                "crew": "Utility company / licensed electrician; tank inspector",
                "references": ["NFPA 70 (National Electrical Code)", "AWWA D100 / D103 (water storage tanks)"],
            },
            "security_and_access": {
                "steps": [
                    "Secure openings and fence off unsafe or derelict buildings; post warning signs.",
                    "Clear blocked access roads for emergency vehicles.",
                ],
                "crew": "Property owner / facilities team",
                "references": ["IPMC section 301.3 (vacant structures)"],
            },
            "other": {
                "steps": ["Have a qualified surveyor or engineer review the frame and decide on an inspection or repair."],
                "crew": "Building surveyor",
                "references": [],
            },
        },
    },
    "civil": {
        "name": "Civil Infrastructure & Construction",
        "look_for": (
            "bridges, dams and spillways, roads and highways, culverts, retaining walls, slopes and embankments, "
            "and active construction sites. For existing structures look for concrete cracking, spalling and exposed "
            "rebar, rusted steel members, collapsed or displaced spans and members, erosion, scour and undermining, "
            "washouts, landslides and settlement, pavement potholes and cracking, and blocked or overtopped drainage. "
            "On construction sites look for people working at height without edge protection or harnesses, "
            "unprotected openings and slab edges, unshored excavations, people close to operating plant or suspended "
            "loads, missing hard hats or hi-vis, unsafe material storage, debris, missing silt fences and runoff "
            "control, and missing barriers between the works and the public."
        ),
        "categories": {
            "concrete_damage": "Cracking, spalling, scaling, exposed or rusting rebar, honeycombing, failed joints in concrete.",
            "steel_corrosion": "Rust and section loss on steel girders, beams, bearings, rails, piles or fittings; failed coating.",
            "structural_failure": "Collapsed, broken, displaced or deformed spans, members, walls or structures.",
            "erosion_scour_washout": "Erosion, scour at piers or abutments, undermining, washed-out roads or embankments, spillway erosion.",
            "slope_or_ground_failure": "Landslides, slope movement, settlement, sinkholes, failed retaining walls.",
            "pavement_distress": "Potholes, cracking, rutting, edge break-up or heaving of road and runway surfaces.",
            "drainage_failure": "Blocked, damaged or overtopped culverts, drains and channels; ponding.",
            "construction_safety": "Work at height without edge protection or harness, unprotected openings, unshored excavations, people near operating plant or suspended loads, missing PPE.",
            "site_housekeeping_environment": "Loose materials and debris, unsafe stacking, missing silt fences or sediment control, runoff, dust.",
            "public_protection_traffic": "Missing barriers, fencing or signage between works or hazards and the public or traffic.",
            "other": "Any other anomaly that needs an engineer's attention.",
        },
        "playbook": {
            "concrete_damage": {
                "steps": [
                    "Map the cracks and spalls (width, length, location) and compare with the last inspection.",
                    "Sound the concrete (hammer or chain drag) around spalls to find delamination; check rebar for section loss.",
                    "Remove loose concrete over traffic or walkways now so it can't fall.",
                    "Repair: clean and treat exposed rebar, patch with a repair mortar; inject structural cracks with epoxy; seal non-structural cracks.",
                    "Wide or growing structural cracks need an engineer's load-rating check before the structure stays in full service.",
                ],
                "crew": "Structural/bridge engineer + concrete repair contractor",
                "references": ["ACI 562 (concrete repair code)", "ACI 201.1R (condition survey)", "AASHTO Manual for Bridge Evaluation"],
            },
            "steel_corrosion": {
                "steps": [
                    "Measure remaining thickness at the worst areas (UT or calipers) and note section loss at critical locations.",
                    "Clean bearings, joints and drainage that trap water and debris against the steel.",
                    "Blast and recoat; plate or replace members with significant section loss after an engineer's check.",
                ],
                "crew": "Bridge engineer + coatings/steel repair contractor",
                "references": ["AASHTO Manual for Bridge Evaluation", "FHWA Bridge Inspector's Reference Manual", "SSPC/AMPP coating standards"],
            },
            "structural_failure": {
                "steps": [
                    "Close the structure and the area it could fall onto, including roads, waterways and paths below.",
                    "Emergency engineering assessment: stability of what's still standing and risk of further collapse.",
                    "Stabilise, prop or remove unstable parts under engineer direction; plan detours and navigation closures.",
                    "Preserve evidence for the investigation; notify the regulator (FHWA/NTSB/state DOT for bridges).",
                ],
                "crew": "Structural engineer + owner agency + emergency services",
                "references": ["23 CFR 650 Subpart C (National Bridge Inspection Standards)", "AASHTO Manual for Bridge Evaluation"],
            },
            "erosion_scour_washout": {
                "steps": [
                    "Close the affected road or structure and set a safe setback from the eroding edge; it can keep failing.",
                    "Check foundations, piers and abutments for undermining (probe, sonar or diver for underwater scour).",
                    "Stop the water doing the damage: divert, reduce flow or armour the eroding face (rock riprap, gabions).",
                    "Rebuild the embankment or road with compacted fill, proper drainage and erosion protection; design against the flood that caused it.",
                ],
                "crew": "Geotechnical/hydraulic engineer + earthworks contractor",
                "references": ["FHWA HEC-18 (bridge scour)", "FHWA HEC-23 (scour countermeasures)", "FEMA P-93 (Federal Guidelines for Dam Safety)"],
            },
            "slope_or_ground_failure": {
                "steps": [
                    "Keep people and traffic out of the slide area and below it.",
                    "Survey and monitor movement (survey pins, inclinometers) to see whether it is still moving.",
                    "Drain the slope and remove load from the top; design a fix (buttress, retaining wall, soil nails) with a geotechnical engineer.",
                ],
                "crew": "Geotechnical engineer + earthworks contractor",
                "references": ["FHWA Geotechnical Engineering Circulars", "USACE EM 1110-2-1902 (slope stability)"],
            },
            "pavement_distress": {
                "steps": [
                    "Fill potholes and mark hazards now; seal cracks before water gets into the base.",
                    "Find the cause (drainage, overloading, base failure) with cores or a deflection test before resurfacing.",
                    "Mill and overlay, or reconstruct the base where it has failed.",
                ],
                "crew": "Road maintenance crew / pavement engineer",
                "references": ["FHWA Distress Identification Manual (LTPP)", "MUTCD (temporary traffic control)"],
            },
            "drainage_failure": {
                "steps": [
                    "Clear blockages from culverts, inlets and channels.",
                    "Inspect culvert barrels and outlets for damage and erosion; repair or upsize if it overtops repeatedly.",
                ],
                "crew": "Maintenance crew / hydraulic engineer",
                "references": ["FHWA HDS-5 (culvert design)", "FHWA Culvert Assessment Manual"],
            },
            "construction_safety": {
                "steps": [
                    "Stop the unsafe activity now and brief the crew; the site supervisor must correct it before work restarts.",
                    "Install guardrails or edge protection at slab edges and openings over 6 ft (1.8 m); cover and mark openings.",
                    "Where guardrails aren't possible, use personal fall arrest with proper anchor points.",
                    "Excavations over 5 ft (1.5 m) need shoring, shielding or sloping, and safe access.",
                    "Keep people out of the swing radius of plant and from under suspended loads; enforce hard hats and hi-vis.",
                ],
                "crew": "Site supervisor + safety officer",
                "references": ["OSHA 29 CFR 1926 Subpart M (fall protection)", "OSHA 1926 Subpart P (excavations)", "OSHA 1926 Subpart CC (cranes)"],
            },
            "site_housekeeping_environment": {
                "steps": [
                    "Clear debris and restack materials on level ground away from edges.",
                    "Install or repair silt fences, inlet protection and stabilised entrances to stop sediment leaving the site.",
                ],
                "crew": "Site supervisor",
                "references": ["OSHA 1926.25 (housekeeping)", "EPA Construction General Permit (stormwater)"],
            },
            "public_protection_traffic": {
                "steps": [
                    "Put up barriers, fencing and signs between the hazard and the public or traffic.",
                    "Set up temporary traffic control and detours to the approved plan.",
                ],
                "crew": "Site supervisor / traffic management contractor",
                "references": ["MUTCD Part 6 (temporary traffic control)"],
            },
            "other": {
                "steps": ["Have a qualified engineer review the frame and decide on an inspection or repair."],
                "crew": "Civil engineer",
                "references": [],
            },
        },
    },
    "generic": {
        "name": "General Industrial Asset",
        "look_for": (
            "any industrial infrastructure. Look for leaks, corrosion, cracks, structural damage, missing "
            "components, fire or burn marks, debris, vegetation encroachment and safety hazards."
        ),
        "categories": {
            "leak_or_spill": "Liquid or gas release, stains or pooling.",
            "corrosion": "Rust or metal loss.",
            "structural_damage": "Cracks, dents, deformation, broken or missing parts.",
            "fire_or_heat_damage": "Burn marks, scorching, melted parts.",
            "vegetation_or_debris": "Vegetation or debris on or around the asset.",
            "safety_hazard": "Anything that endangers people: exposed live parts, open edges, missing guards.",
            "other": "Any other anomaly.",
        },
        "playbook": {},
    },
}

GENERIC_STEPS = {
    "steps": [
        "Send a qualified inspector to confirm the finding from the ground.",
        "Decide on repair or replacement based on the on-site measurement.",
    ],
    "crew": "Qualified inspector",
    "references": [],
}


def repair_guidance(profile_key: str, category: str) -> dict:
    return PROFILES[profile_key]["playbook"].get(category, GENERIC_STEPS)


def actions_for(profile_key: str) -> dict:
    return PROFILES[profile_key].get("actions", ACTIONS)


def action_label(profile_key: str, action: str) -> str:
    return PROFILES[profile_key].get("action_labels", ACTION_LABELS).get(action, action.replace("_", " "))
