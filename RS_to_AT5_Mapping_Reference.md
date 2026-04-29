# Rocksmith+ → AmpliTube 5 Gear Mapping Reference

Generated April 2026 · Accompanies `rs_to_at5.py`

---

## Methodology & Data Sources

All AmpliTube 5 GUIDs were extracted directly from the `AmpliTube 5.pak` archive on a live installation, from the GearInfo JSON files embedded within it. GUIDs were cross-validated against real `.at5p` preset files saved from the application. No GUIDs were guessed or inferred from documentation.

Rocksmith+ tone keys were sourced from a scrape of 1,228 unique tones across 13,623 songs via the IBEX public API. All Rocksmith+ knob values use a **0–100 float scale**; AmpliTube 5 uses a **0–10 physical knob scale**. Conversion: `AT5 value = RS value ÷ 10`.

**Match quality key used in tables below:**
- `Exact` — same real-world hardware modelled on both sides
- `Assumed` — closest available model where a direct equivalent was not found
- `Good` — effect type matches closely
- `Approx` — different effect type used as the nearest sonic equivalent

---

## Signal Chain Mapping

| Rocksmith+ Slot | AmpliTube 5 Section | Notes |
|---|---|---|
| `PrePedal1`, `PrePedal2` | `StompA1` – Slots 0 & 1 | Pre-amp stomp pedals |
| `Amp` | `AmpA` | Single active amp; AmpB/C muted |
| `Cabinet` | `CabA` – CabModel + SpeakerModel0–3 | Enclosure + 4 speaker drivers (pairs A/B) |
| `Rack1`, `Rack2` | `RackA` – Slots 0 & 1 | First two rack effects |
| `Rack3`, `Rack4` | `RackB` – Slots 0 & 1 | Second two rack effects |
| `PostPedal1`, `PostPedal2` | `StompB1` – Slots 0 & 1 | Post-amp stomp pedals |

> AmpliTube 5 supports three parallel amp/cab paths (A/B/C). The converter populates Path A only; B and C are set to `Mute="1"`. StompA2, StompB2, StompB3 and all LoopFx slots are also muted.

---

## Knob Name Mapping

Rocksmith+ stores knob values with keys in the format `Amp_{AmpKey}_{KnobName}`. The suffix after the last underscore is extracted and translated to the AT5 parameter name.

| RS Knob Suffix | RS Meaning | AT5 Param Name | Notes |
|---|---|---|---|
| `Bass` | Bass | `Bass` | Direct |
| `Mid` | Middle | `Middle` | RS uses `Mid`; AT5 uses `Middle` |
| `Treble` | Treble | `Treble` | Direct |
| `Pres` / `Presence` | Presence | `Presence` | RS may use abbreviation |
| `Loudness1` | Volume (ch1) | `Volume` | Marshall Plexi dual-volume type |
| `Loudness2` | Volume (ch2) | `Volume2` | Second volume on Plexi types |
| `Master` | Master volume | `Master` | Direct |
| `Gain` | Gain/Drive | `Gain` | Direct |
| `PreAmp` | Pre-amp gain | `PreAmp` | Direct |
| `Sensitivity` | Sensitivity | `Sensitivity` | Direct |

> **Known limitation:** AT5 parameter names in the `.at5p` XML include a model-specific suffix (e.g. `Bass_JCM800AT4`). The converter emits only the base name (e.g. `Bass`). Knobs may appear at their AT5 defaults on load for some amps until this is resolved.

---

## Amplifier Mapping

Source: `GearInfo/Cabs.json` (112 models). Note: IK Multimedia's internal file naming is inverted — the file named `Cabs.json` contains the amp database.

| Rocksmith+ Key | Real-World Amp | AmpliTube 5 Model | AT5 GUID | Match |
|---|---|---|---|---|
| `Amp_MarshallPlexi` | Marshall 1959 Super Lead | British Lead S100 | `d089ef66-b5c4-4274-910c-6a6ee194cf04` | Exact |
| `Amp_MarshallJCM800` | Marshall JCM800 | Brit 8000 | `8fe96936-5178-4950-9b80-d89c32534bad` | Exact |
| `Amp_MarshallJCM900` | Marshall JCM900 | Brit 9000 | `cbf3c00f-dc31-4c7f-a409-f7fdbca005a8` | Exact |
| `Amp_MarshallJTM45` | Marshall JTM45 | JH Gold | `7788f707-4ef2-44cd-862a-a82ffdf7172b` | Exact |
| `Amp_MarshallSilverJubilee` | Marshall Silver Jubilee | Brit Silver | `3930eb8b-3eda-4079-b86d-7bfd7d4449bc` | Exact |
| `Amp_MarshallMajor` | Marshall Major | Red Pig | `e1eed2cf-6777-46c4-ada2-65df0d7afc46` | Exact |
| `Amp_MarshallJMP` | Marshall JMP100 | Vintage Metal Lead | `1b5961b1-f862-4c8a-9a9b-a920da8c5cc2` | Assumed |
| `Amp_MarshallSlash` | Marshall AFD100 | Brit 100 Mod 34/36 | `2ea3ecfb-1b0c-417a-8788-86f5915f43c5` | Assumed |
| `Amp_MarshallSlashGold` | Marshall 2555SL | Brit L.A. Gold | `155f0121-a2ee-4e16-aaa0-44948f9be44f` | Assumed |
| `Amp_MarshallJVM` | Marshall JVM410 | Satch VM | `57c43635-a976-46e0-a5c1-ef843bbba616` | Assumed |
| `Amp_FenderDeluxeReverb` | Fender '65 Deluxe Reverb | '65 Deluxe Reverb | `89b3caab-dffb-4c29-85d9-2a60cb93c566` | Exact |
| `Amp_FenderTwinReverb` | Fender '65 Twin Reverb | '65 Twin Reverb | `b3869f27-a9f1-4482-add4-9512c16917ea` | Exact |
| `Amp_FenderBassman` | Fender Bassman (Silverface) | American Vintage B | `ca4587b9-3960-49de-9509-5a61e9b5cbae` | Assumed |
| `Amp_FenderSupersonic` | Fender Super-Sonic | Super-Sonic | `f4b89ab3-8ca6-44ee-b90b-a570040c8a3d` | Exact |
| `Amp_FenderVibroking` | Fender Vibro-King | Vibro-King | `dffa559d-7b12-464a-9fbf-877ca25f5cf3` | Exact |
| `Amp_FenderVibroverb` | Fender '64 Vibroverb | '64 Vibroverb Custom | `f0951b1e-91d2-4360-80d7-793fa785d2d6` | Exact |
| `Amp_FenderChamp` | Fender '57 Champ | '57 Champ | `5f4f50a1-d5cb-43be-ad11-084e4ff21ea6` | Exact |
| `Amp_FenderChampion600` | Fender Champion 600 | Champion 600 | `016a8c2a-489e-49da-81d7-5b72feb60f74` | Exact |
| `Amp_FenderPrinceton` | Fender '65 Princeton | '65 Princeton | `2a1f483c-a136-45b6-81ec-e92c60f8d009` | Exact |
| `Amp_FenderProJunior` | Fender Pro Junior | Pro Junior | `d0546d04-505c-42b1-8e9e-668a16adcfa8` | Exact |
| `Amp_FenderSuperReverb` | Fender '65 Super Reverb | '65 Super Reverb | `d3c791b9-58f1-41d2-8a88-797e98cc5b29` | Exact |
| `Amp_Fender57CustomTwin` | Fender '57 Custom Twin-Amp | '57 Custom Twin-Amp | `4c9e667b-932a-42e3-a5d8-a9d9374c9959` | Exact |
| `Amp_Fender57CustomPro` | Fender '57 Custom Pro-Amp | '57 Custom Pro-Amp | `6c421302-9602-4ee8-b94a-672aa24cdde4` | Exact |
| `Amp_Fender59Bassman` | Fender '59 Bassman LTD | '59 Bassman LTD | `3fcc8ad1-6d5e-416d-9c3d-7aae91c6f4d4` | Exact |
| `Amp_FenderBassman300` | Fender Bassman 300 | Bassman 300 | `9e6f407a-161d-433b-bddc-8565103fc9ce` | Exact |
| `Amp_MesaBoogieMarkIII` | Mesa/Boogie Mark III | Mark III | `6ec4bf7a-dc59-4443-b2fb-1e645bf5192c` | Exact |
| `Amp_MesaBoogieMarkIV` | Mesa/Boogie Mark IV | Mark IV | `1fbf7d6e-dad8-470f-b204-4d96b5466893` | Exact |
| `Amp_MesaBoogieMarkV` | Mesa/Boogie Mark V | Mark V | `d31154a9-8b5f-4abf-b079-d2e728d2c564` | Exact |
| `Amp_MesaBoogieMarkIIC` | Mesa/Boogie Mark IIC+ | Mark IIC+ | `6e5c01fe-e1be-4e91-8657-74718ac8cb6e` | Exact |
| `Amp_MesaDualRectifier` | Mesa/Boogie Dual Rectifier | Dual Rectifier | `75ad4a0e-5c75-443d-8617-9681c4fe58d3` | Exact |
| `Amp_MesaTripleRectifier` | Mesa/Boogie Triple Rectifier | Triple Rectifier | `c85e5dc4-d051-4aad-846f-038b0b5233c5` | Exact |
| `Amp_MesaTA30` | Mesa TransAtlantic TA-30 | TransAtlantic TA-30 | `1284c9cc-6efa-4720-a0da-106a2d2af1d8` | Exact |
| `Amp_MesaTripleCrown` | Mesa Triple Crown | Triple Crown | `2ed4e896-6cf4-40ee-bc12-15f0c4d38b65` | Exact |
| `Amp_MesaCaliforniaTweed` | Mesa California Tweed | California Tweed | `d9aa41f9-4e51-4719-929c-251d07f2f276` | Exact |
| `Amp_VoxAC30` | Vox AC30 | British Copper 30TB | `5d235e0d-9fd7-429e-b483-6f815281f3d7` | Exact |
| `Amp_VoxAC30Blue` | Vox AC30 (Blue Alnico) | British Blue Tube 30TB | `533d3c6c-b3cd-455c-a3a1-642016f5cda9` | Exact |
| `Amp_OrangeOR120` | Orange OR120 | OR-120 | `6e8690b3-f6cf-4c36-b3c2-7f38fcc5706e` | Exact |
| `Amp_OrangeTinyTerror` | Orange Tiny Terror | Tiny Terror | `99e446c7-49df-45b1-bff9-26d95e10c763` | Exact |
| `Amp_OrangeRockerverb` | Orange RockerVerb 50 | RockerVerb 50 | `e6151532-1028-422c-9a5d-fc57594ce8e8` | Exact |
| `Amp_OrangeAD30` | Orange AD30 | AD 30 | `dd7b0e06-a17a-4851-83c4-ee32ca303b01` | Exact |
| `Amp_OrangeThunderverb` | Orange Thunderverb 200 | Thunderverb 200 | `e3260631-d81f-4c76-9e4f-d12be6ede5cb` | Exact |
| `Amp_OrangeAD200` | Orange AD200B (bass) | AD 200 | `dfb00647-6603-4fe1-a67a-5690a4dad0fb` | Exact |
| `Amp_OrangeDualTerror` | Orange Dual Terror | Dual Terror | `3c25674f-a418-4fec-863c-f94495c746a0` | Exact |
| `Amp_EnglE650` | ENGL E650 | E650 | `c936fc9c-1594-48c8-b561-824827452a66` | Exact |
| `Amp_EnglPowerball` | ENGL Powerball | Powerball | `88d927a0-e399-4a1d-ac68-0699eee85f02` | Exact |
| `Amp_Soldano` | Soldano SLO-100 | SLD 100 | `4a22ac9f-aabb-4180-b697-5d5710a1acc2` | Exact |
| `Amp_Peavey5150` | Peavey 5150 | Metal Lead V | `dcc7c825-76f4-4703-8e1f-b8a12b30b1de` | Assumed |
| `Amp_Hiwatt` | Hiwatt DR103 | HiAmp | `26fbbf20-f88e-46de-a76f-5aabd2c8fd8d` | Exact |
| `Amp_RolandJC120` | Roland Jazz Chorus JC-120 | Jazz Amp 120 | `ac08939a-32bf-496c-96ac-5d6c530abf14` | Exact |
| `Amp_DrZMaz18` | Dr. Z MAZ 18 Jr. | MAZ 18 Jr | `abdcae70-bff2-4b02-bf2f-d716dd8e8adf` | Exact |
| `Amp_DrZZWreck` | Dr. Z Z Wreck | Z Wreck | `cc59b472-2a2f-40b1-97f4-6ee4b7536c87` | Exact |
| `Amp_DiezelVH4` | Diezel VH4 | VHandcraft 4 | `185e9cde-535b-42ab-abd1-4fbdb52d4808` | Exact |
| `Amp_BognerEcstasy` | Bogner Ecstasy | German 34 | `4b13e59f-32b7-4a69-abd0-28d0909cef89` | Assumed |
| `Amp_PRSArchon` | PRS Archon | SilverPlate 50 | `f24511a1-8ade-4f93-b781-ade541f0a921` | Assumed |
| `Amp_Ampeg` | Ampeg SVT Classic | SVX-CL | `52f28b23-80e3-4f43-9508-4447258b11c0` | Assumed |
| `Amp_AmpegSVTVR` | Ampeg SVT-VR | SVX-VR | `2aa0f50f-a6c9-4edd-97c2-df71a24087db` | Assumed |

---

## Cabinet Mapping

Each Rocksmith+ cabinet key maps to two AT5 components:
- **Enclosure** (`CabModel` GUID) — from `GearInfo/Mics.json` (108 models)
- **Speaker driver** (`SpeakerModel` GUID) — from `GearInfo/Stomps.json` (33 models)

AT5 has four speaker driver slots per cab. The converter assigns driver A to slots 0 & 1, and driver B to slots 2 & 3.

| RS Cab Key | RS Description | AT5 Enclosure | AT5 Speaker Driver | Enclosure GUID | Speaker GUID |
|---|---|---|---|---|---|
| `Cab_Marshall1960TV_57_Cone` | Marshall 1960TV (4×12) | 4×12 Brit 8000 | Brit Anniversary 1 (G12H) | `7c0b8ce1-…` | `674b563d-…` |
| `Cab_Marshall1960A` | Marshall 1960A (4×12) | 4×12 Brit 8000 | Brit 75 (G12T-75) | `7c0b8ce1-…` | `e372dd04-…` |
| `Cab_Marshall1960B` | Marshall 1960B (4×12) | 4×12 Brit 8000 | Brit 75 (G12T-75) | `7c0b8ce1-…` | `e372dd04-…` |
| `Cab_Marshall1960AV` | Marshall 1960AV (4×12) | 4×12 1960AV | Brit Anniversary 1 (G12H) | `c97bc69c-…` | `674b563d-…` |
| `Cab_MarshallSilver` | Marshall Silver Jubilee cab | 4×12 Brit Silver | Brit Silver (V12-60) | `c6dc5147-…` | `93ece316-…` |
| `Cab_MarshallJCM800` | Marshall JCM800 cab | 4×12 Brit 8000 | Brit 75 (G12T-75) | `7c0b8ce1-…` | `e372dd04-…` |
| `Cab_VoxAC30` | Vox AC30 cabinet | 2×12 BM 30 H70 | Brit Alnico B (Blue) | `85d85251-…` | `aa7f635a-…` |
| `Cab_VoxAC30Blue` | Vox AC30 Blue Alnico | 2×12 BM 30 Blue | Brit Alnico B (Blue) | `72b72d5c-…` | `aa7f635a-…` |
| `Cab_FenderDeluxeReverb` | Fender Deluxe Reverb combo | 1×12 Open Vintage | American 12C (Jensen) | `bcec521d-…` | `a3cc18b8-…` |
| `Cab_FenderTwinReverb` | Fender Twin Reverb | 2×12 '65 Twin Reverb | American Alnico (Jensen) | `8b37839c-…` | `02079eab-…` |
| `Cab_FenderBassman` | Fender Bassman cab | 4×10 '59 Bassman | American 12C (Jensen) | `4614704e-…` | `a3cc18b8-…` |
| `Cab_MesaRecto` | Mesa Rectifier cab (4×12) | 4×12 Recto Traditional Slant | Brit V2 (V30 Mesa) | `849b3340-…` | `2dc1a3c4-…` |
| `Cab_MesaTA30` | Mesa TA-30 cab | 2×12 TransAtlantic | Brit Vintage 16B (V30) | `356da432-…` | `9422a3d9-…` |
| `Cab_OrangePPC412` | Orange PPC412 | 4×12 PPC 412 | Brit Vintage 16B (V30) | `4edd00f5-…` | `9422a3d9-…` |
| `Cab_OrangePPC212` | Orange PPC212 | 2×12 PPC 212 | Brit Vintage 16B (V30) | `16b2e136-…` | `9422a3d9-…` |
| `Cab_OrangeTinyTerror` | Orange Tiny Terror cab | 1×12 Tiny Terror | Brit Vintage 16B (V30) | `33238dfe-…` | `9422a3d9-…` |
| `Cab_EnglE412PROXXL` | ENGL E412 PRO XXL | E 412 PRO XXL | Brit Vintage 16B (V30) | `8eaae0e6-…` | `9422a3d9-…` |
| `Cab_Hiwatt` | Hiwatt cab (4×12) | 4×12 HiAmp | HiAmp (Fane) | `9ef10de4-…` | `d052f84c-…` |
| `Cab_RolandJC120` | Roland JC-120 cab | 2×12 JP Jazz | Jazz 12 (Roland) | `f7902634-…` | `f755dce5-…` |
| `Cab_AmpegSVT810E` | Ampeg SVT-810E | SVX-810E | Brit Vintage 16B (fallback) | `b11418d6-…` | `9422a3d9-…` |

> Full GUIDs are truncated here for readability. Complete values are in `rs_to_at5.py` in the `CAB_ENCLOSURE_MAP` and `SPEAKER_MAP` dictionaries. Unknown cab keys fall back to a size-inferred default: 4×12, 2×12, or 1×12.

---

## Effects Mapping

Rocksmith+ uses `Rack_Studio*` style keys for all effects regardless of whether they appear in rack or stomp slots. The converter also carries a full lookup table of all 115 AT5 stomp models (recovered from `GearInfo/Amps.json` at raw pak offset `0x671782`) for fuzzy matching of any additional effect keys.

### Primary Rack_Studio* Mappings

| Rocksmith+ Key | RS Description | AmpliTube 5 Effect | AT5 GUID | Match |
|---|---|---|---|---|
| `Rack_StudioComp` | Studio Compressor | Compressor | `5478981b-b18a-469f-81e7-a3e228cc9d50` | Good |
| `Rack_StudioEQ` | Studio EQ | 7 Band Graphic EQ | `8d7ff76e-9273-46b6-95d5-3d7bd667fff2` | Good |
| `Rack_StudioDelay` | Studio Delay | Delay | `e11b1dc5-1f7d-42ad-af30-0539b3646b3c` | Good |
| `Rack_StudioChorus` | Studio Chorus | Chorus | `bc6a9f33-ac11-41f8-973d-0327d4f3e018` | Good |
| `Rack_StudioFlanger` | Studio Flanger | Flanger | `7ccf016f-e540-4e46-a124-8f19ce5ab2b1` | Good |
| `Rack_StudioPhaser` | Studio Phaser | Phaze Nine (MXR Phase 90) | `a4ed5e25-707d-40ef-9846-64eeb820aeea` | Good |
| `Rack_StudioWah` | Studio Wah | Wah (Cry Baby) | `6482748e-9382-4ad6-b284-5c29ee50f2d7` | Good |
| `Rack_StudioVibrato` | Studio Vibrato | Uni-V (Univibe) | `a6d48956-a0e5-4d63-9c22-b5b38604d2a5` | Approx |
| `Rack_StudioTremolo` | Studio Tremolo | Opto Tremolo (Fender) | `50378f09-a919-4dee-9bbe-c242403a52a2` | Good |
| `Rack_StudioChamber` | Studio Chamber Reverb | '63 Reverb (Fender spring) | `ad9d0a70-7a59-4fef-ace5-c592764e3749` | Approx |
| `Rack_StudioReverb` | Studio Reverb | '63 Reverb (Fender spring) | `ad9d0a70-7a59-4fef-ace5-c592764e3749` | Approx |
| `Rack_StudioPitch` | Studio Pitch | Pitch Shifter | `e2b29e5c-33a0-41f0-9d54-dc749d371fe0` | Good |
| `Rack_StudioNoise` | Studio Noise/Gate | Noise Gate | `0455f997-43ca-4c9b-9269-286a19d10d48` | Good |
| `Rack_StudioBoost` | Studio Boost | Booster (MXR CAE) | `77f0f320-cc4e-44be-9ffe-2f0b679434ae` | Good |
| `Rack_StudioOD` | Studio Overdrive | Overdrive (Boss SD-1) | `fd627f5e-ba11-4082-b546-a4f0b05985ff` | Good |
| `Rack_StudioDist` | Studio Distortion | Distortion (Boss DS-1) | `510f6d25-6ec4-417b-bf58-0f8028209cce` | Good |
| `Rack_StudioFuzz` | Studio Fuzz | BigPig (EHX Big Muff) | `58dbec22-58e0-464c-8c04-91fb9d9973e2` | Good |

### Full AT5 Stomp Model Reference

All 115 stomp models available in AmpliTube 5, used for fuzzy matching. Source: `GearInfo/Amps.json` recovered from pak at byte offset `6,755,621`.

| Model # | AT5 Name | Real-World Equivalent | GUID |
|---|---|---|---|
| 0 | Empty | *(null slot)* | `773b8ea7-b54a-4a3c-99df-ffbbf6d29271` |
| 1 | Delay | AmpliTube Delay | `e11b1dc5-1f7d-42ad-af30-0539b3646b3c` |
| 2 | EchoMan | EHX Memory Man | `48e7b721-d57a-4c34-813b-95d8091d5eda` |
| 3 | EP Tape Echo | Maestro Echoplex | `907ecdf1-15be-4f41-b56d-2705e7bb89ae` |
| 4 | TapDelay | AmpliTube Tap Delay | `96b57f95-4380-444a-8c0a-fbcc9bef1dd9` |
| 5 | BigPig | EHX Big Muff Pi | `58dbec22-58e0-464c-8c04-91fb9d9973e2` |
| 6 | Crusher | AmpliTube Crusher | `305c9b6b-04cf-4673-b58a-e62afb4fefcb` |
| 7 | Diode Overdrive | AmpliTube Diode OD | `5e65abef-82eb-4995-b911-d5eca4f8291e` |
| 8 | Distortion | Boss DS-1 | `510f6d25-6ec4-417b-bf58-0f8028209cce` |
| 9 | Feedback | Boss DF-2 | `395ed825-f3e8-40c1-8d69-34d8b23c9100` |
| 10 | Metal Distortion | Boss MT-2 | `1910832b-2b47-46ff-b14c-46ec168e50e6` |
| 11 | Metal Distortion 2 | Boss HM-2 | `e5c8acd3-3771-4df9-8d2e-ee33c8dd3d21` |
| 12 | Overdrive | Boss SD-1 | `fd627f5e-ba11-4082-b546-a4f0b05985ff` |
| 13 | OverScream | Ibanez Tube Screamer | `fa1de2e2-102b-4edf-b3b5-23ceaeddedf0` |
| 14 | PROdrive | ProCo RAT | `9b672f82-2832-4134-8db7-5cb9147c69a3` |
| 15 | The Ambass'dor | Marshall Guv'Nor | `c8b142b0-4480-4d79-bc5c-f0232440ce05` |
| 16 | Compressor | AmpliTube Compressor | `5478981b-b18a-469f-81e7-a3e228cc9d50` |
| 17 | Dcomp | MXR Dynacomp | `26c75920-d4bf-4e5e-900f-f78c70e06c17` |
| 18 | 7 Band Graphic | AmpliTube Graphic EQ | `8d7ff76e-9273-46b6-95d5-3d7bd667fff2` |
| 19 | 10 Band Graphic | MXR 10 Band Equalizer | `babadeaf-9c28-4641-8fa9-d7366a3238a2` |
| 20 | Envelope Filter | AmpliTube Envelope Filter | `77a321dd-69e1-4474-be07-d8a97e78bd1f` |
| 21 | LFO Filter | AmpliTube LFO Filter | `390c602d-5834-417d-bf0c-cafe544c5869` |
| 22 | Rezo | AmpliTube Rezo | `327d6d53-b6cb-4d33-bdaf-620fb52c20ec` |
| 23 | Step Filter | AmpliTube Step Filter | `25425c78-31db-48f4-ad57-09f41e0e1291` |
| 24 | Wah | Dunlop Cry Baby | `6482748e-9382-4ad6-b284-5c29ee50f2d7` |
| 25 | Wah 10 | Ibanez WH-10 | `2de5239a-78d6-4a01-82e6-2ea3afb60501` |
| 26 | Wah 46 | Vox V846 | `bc86a019-ffd5-4b71-8bfe-5913e3d58d7c` |
| 27 | Wah 47 | Vox V847 | `02cd5797-10d8-4ffa-b4f4-438b93028941` |
| 28 | Nu-Tron III | Musitronics Mu-Tron | `0332d916-2ab2-4b7d-98c4-73a80a42b3b1` |
| 29 | Class Fuzz | Roger Mayer Classic Fuzz | `8beec4ce-fb43-4f81-935a-3b5cb3695c8b` |
| 30 | Fuzz Age | Arbiter Fuzz Face | `6c3ff0bf-b840-47f3-83d3-66816763097f` |
| 31 | Fuzz Age 2 | Arbiter Fuzz Face (v2) | `09ac5b94-f238-4e4c-914e-ba7662f280d9` |
| 32 | FuzzOne | Maestro FuzzTone | `0679dea3-2588-4d9d-8d0d-ef3762f1f478` |
| 33 | Octa-V | Roger Mayer Octavia | `aa74a915-a1fe-4f54-a8a8-5297c3e09b56` |
| 34 | RightFuzz | Mosrite Fuzzrite | `b0f5949f-4825-4202-92a0-c5817f493116` |
| 35 | XS Fuzz | Roger Mayer Axis Fuzz | `64e7c1cd-b860-40c7-930b-6d820b1ffa77` |
| 36 | Analog Flanger | Boss BF-2 | `ae6177c2-27c2-4463-a06a-357408bb2082` |
| 37 | Chorus | AmpliTube Chorus | `bc6a9f33-ac11-41f8-973d-0327d4f3e018` |
| 38 | Chorus-1 | Roland/Boss CE-1 | `2a9ef349-fb29-4e66-99a9-cc66d10192cc` |
| 39 | Electric Flanger | EHX Electric Mistress | `8a878202-9126-4d20-8e73-374e178312f4` |
| 40 | Flanger | AmpliTube Flanger | `7ccf016f-e540-4e46-a124-8f19ce5ab2b1` |
| 41 | Metal Flanger | MXR Flanger 117 | `4e4d82f9-224a-4ffb-9994-97ef8285c315` |
| 42 | Opto Tremolo | Fender Opto-Tremolo | `50378f09-a919-4dee-9bbe-c242403a52a2` |
| 43 | Phaze Nine | MXR Phase 90 | `a4ed5e25-707d-40ef-9846-64eeb820aeea` |
| 44 | Phazer10 | MXR Phaser 100 | `cc424097-15e5-47d3-abb9-3925073ac22b` |
| 45 | Small Phazer | EHX Small Stone | `0ef53d8f-2dd5-4acd-95f8-e8652ae31240` |
| 46 | Uni-V | Univox Uni-Vibe | `a6d48956-a0e5-4d63-9c22-b5b38604d2a5` |
| 47 | Harmonator | AmpliTube Harmonator | `46f09ab5-ffd9-4c5b-8eec-681f880d4530` |
| 48 | Octav | Boss OC-2 | `994770ae-ebb4-4ca8-884e-374f88fa3db0` |
| 49 | Pitch Shifter | AmpliTube Pitch Shifter | `e2b29e5c-33a0-41f0-9d54-dc749d371fe0` |
| 50 | Wharmonator | DigiTech Whammy | `9b8e89e2-2959-41b2-90eb-dc5de12964d0` |
| 51 | Acoustic Sim | AmpliTube Acoustic Sim | `71fe6e6d-5879-42a7-9a31-6093ecee2a1c` |
| 52 | Volume | AmpliTube Volume | `de12969a-31cc-4985-b4cf-289d2970823d` |
| 53 | Step Slicer | AmpliTube Step Slicer | `66410529-1158-4d6e-a33a-474541a64571` |
| 54 | Swell | AmpliTube Swell | `ca453f6e-7af5-4e90-90df-ff954b17ecc2` |
| 55 | SVX-OD | Ampeg SCP-OD | `1d665fde-1a62-42a1-be6d-bad9bbe5df3d` |
| 56 | SVX-OCT | Ampeg SCP-OCT | `9afc331b-c0c3-4592-b03f-c97f8d911e34` |
| 57 | Analog Chorus | Ampeg Analog Chorus | `ed2c3a06-d304-496b-b031-7725a3d27eea` |
| 58 | Analog Delay | Ampeg Analog Delay | `b756e0c1-7685-4b38-bccc-b74c7febd868` |
| 59 | Bass Wah | Ampeg Bass Wah | `01cadfae-3ced-4ea6-8676-29a7e6c920b2` |
| 60 | SVX Compressor | Ampeg Compressor | `8a24aa96-f0ae-4e1c-a534-6671e245a690` |
| 61 | SVX Envelope Filter | Ampeg Envelope Filter | `15b140e0-3e02-4adc-a9c4-c652960e60f9` |
| 62 | SVX Volume | Ampeg Volume | `7b1dc197-a4ac-41cc-8b1e-d8ed4102f432` |
| 63 | Star Gate | Brian May Gate | `590df33c-23a6-4d35-bd49-b5b589ffd248` |
| 64 | Red Special | Brian May Red Special | `97c9c8d9-2f26-4126-98f7-64fbc60765ca` |
| 65 | Treble Booster | KAT Treble Booster | `382fd7fe-b60f-440b-aed8-3dae6e9e94c6` |
| 66 | May Wah | Dunlop Cry Baby (BM) | `23c22c20-42ec-472f-84cf-2ae6b20f6f3b` |
| 67 | FOX Phaser | fOXX Foot Phaser | `92605dfc-4716-49ef-944f-fd8c86d76bb2` |
| 68 | 6 Band EQ | MXR 6 Band EQ | `53d32ff2-4726-40d8-93ef-70f23fd36b73` |
| 69 | Pre EQ 3 | Furman PQ-3 | `07bbabf3-09b7-4042-ad30-5a62ff6b1a0c` |
| 70 | Dime Noise Gate | Rocktron Hush IIB | `5aa37004-52de-4846-bb7b-1816d98562de` |
| 71 | Dime Wah | Dunlop Cry Baby GCB95 | `27cd0940-620d-401c-abe2-c9d541673cf6` |
| 72 | Flanger Doubler | MXR Flanger Doubler | `b3703de8-ff21-4f1e-aa89-364eeed3cb57` |
| 73 | Blender | Fender Blender | `01648ef1-6369-4170-81a3-90dd20451260` |
| 74 | Fender Volume | Fender Volume | `01776ae8-8442-4633-b5f7-6bfdaf423ccb` |
| 75 | Fender Wah | Fender Cyber-Twin Wah | `75f96017-8a09-41fd-9979-75bf8bf81645` |
| 76 | Fuzz Wah | Fender Fuzz Wah | `a58d91b0-d7c5-4d3d-8a9a-5c8b75335502` |
| 77 | Phaser | Fender Phaser | `6178531f-d021-43c0-8922-858ffa085746` |
| 78 | Tremolo | Fender Tube Tremolo | `187eb9ab-7ae6-4797-954b-079de09e26bb` |
| 79 | '63 Reverb | Fender '63 Spring Reverb | `ad9d0a70-7a59-4fef-ace5-c592764e3749` |
| 80 | Tape Echo | Fender Cyber-Twin Tape Echo | `8bbfc5b9-bf29-4a55-8211-ca21dcfda8bf` |
| 81 | Fender Compressor | Fender Cyber-Twin Compressor | `f5edced9-6dfc-4851-8651-f81f5423d210` |
| 82 | OCD | Fulltone OCD | `7c499158-084f-49b1-9543-f7e9acc122e0` |
| 83 | Contour Wah | Morley Contour Wah | `487cd1a4-834e-45b2-b5be-6a424cc6a123` |
| 84 | Power Grid | Seymour Duncan Power Grid | `16daf2e6-1c56-4abe-97c9-1fffe2b22bb2` |
| 85 | Shape Shifter | Seymour Duncan Shape Shifter | `96ae9a18-1c2b-48cc-843a-851adb43c091` |
| 86 | DDelay | Boss DD-3 | `4468f4f7-0068-4b8b-ac2b-99e13113fe2d` |
| 87 | Booster | MXR/CAE MC401 | `77f0f320-cc4e-44be-9ffe-2f0b679434ae` |
| 88 | Gate | MXR Smart Gate | `d3e05ec0-2c7b-498a-adc0-b263e853ad30` |
| 89 | OctoBlue | MXR Blue Box Octave Fuzz | `967e57ac-b67d-4b97-942e-aca407e306e0` |
| 90 | X-Chorus | MXR M134 | `5f3947b1-6a09-4570-9f9c-1cc53a7fd88f` |
| 91 | WahDist | Dunlop Slash SW95 | `88863a3a-cfe3-4e86-b735-1303c511bf5f` |
| 92 | Moller | T-Rex Moller | `1d03a910-c5a3-461e-a43a-485ddf3d84ef` |
| 93 | Mudhoney | T-Rex Mudhoney | `e5644c95-e382-4cfe-9c1f-85451017771d` |
| 94 | Replica | T-Rex Replica | `bf72ebc2-a539-4cd2-9204-2d91e9d573df` |
| 95 | Nirvana | Wampler Nirvana Chorus/Vib | `b1ad4a5d-1ad2-4b32-8532-945b869409e3` |
| 96 | Pinnacle Deluxe | Wampler Pinnacle Deluxe | `8a96f6a6-49af-41fb-ab36-a62a18f17def` |
| 97 | Seek Trem | Z.Vex Seek Trem | `86875e91-6fbd-4198-a45c-a06119e6a967` |
| 98 | Seek Wah | Z.Vex Seek Wah | `0ba47121-179c-4d42-bbb6-c3e81bb4f7af` |
| 99 | Satch Wah | Vox Big Bad Wah | `ecc79add-83b7-46ae-896a-3f1c02ece992` |
| 100 | Satch Dist | Boss DS-1 (Satch) | `67f25e2b-1c3f-40ff-9ad2-635d782416af` |
| 101 | Satch Overdrive | Boss OD-1 (Satch) | `fc48618d-3dc3-4d3a-9183-fa3362bd277d` |
| 102 | Tube Overdrive | Chandler Tube Driver | `be3bb897-6e7d-4d9a-ba58-8a034919dc3b` |
| 103 | Satch Octave | Ultimate Octave | `84de10c4-22cf-4e69-9c2d-b7fbc7a8cea2` |
| 104 | SSTE | Fulltone Solid State Tape Echo | `28bb2c33-0bdf-44f7-9274-2eca934cbbff` |
| 105 | AmpLess | Tech21 Sansamp | `d36a32bf-200c-4906-93b9-0aa91cd1f579` |
| 106 | VariDiode+ | MXR Distortion+ | `dbeca376-df39-45c1-b63e-3ee55b747b00` |
| 107 | Noise Gate | *(generic)* | `0455f997-43ca-4c9b-9269-286a19d10d48` |
| 156 | X-VIBE | X-GEAR multi-modulation | `6db46983-d9ff-4ebf-a1eb-d59789bdd501` |
| 157 | X-DRIVE | X-GEAR multi-distortion | `b0b9f092-704a-4232-bac4-c13b4cda902a` |
| 158 | X-SPACE | X-GEAR multi-reverb | `3889d7a5-4131-4c1d-b94e-6d37dcedefc4` |
| 159 | X-TIME | X-GEAR multi-delay | `063668e9-2af7-4a21-a554-abb1ff51a913` |
| 161 | Oil Can Delay | Morley EVO-1 | `b592ab1d-0de9-4814-8d7c-9d96ffe558db` |
| 162 | Power Wah Fuzz | Morley PWF | `1636cd4e-e31f-4817-be9c-244f3dfbe77d` |

---

## Known Gaps & Limitations

1. **Amp knob parameter name suffixes** — AT5 uses model-specific suffixes in parameter names (e.g. `Bass_JCM800AT4`). The converter emits only the base name (e.g. `Bass`). Knobs may appear at their AT5 defaults on load for some amps; this needs per-amp verification.

2. **Effect knob values not transferred** — Effects are placed in the correct slots and marked active (`Bypass="0"`) but all knob positions use AT5 defaults. Mapping effect parameters requires further reverse engineering of the per-effect AT5 XML format.

3. **Stomp database recovery** — The stomp database (`GearInfo/Amps.json`) is at a corrupted offset in the pak index (points to an OTF font). It was recovered by scanning for known content at raw byte offset `6,755,621`. Models outside the recovered 44 KB window may be absent.

4. **Unknown amp/cab/effect keys** — The converter falls back to fuzzy substring matching, then to sensible defaults. All fallbacks are logged as warnings during conversion.

5. **Cabinet enclosure GUIDs** — 50+ specific enclosures are mapped. Unknown cab keys are assigned a size-inferred default based on keywords in the RS key name (`4x12`, `2x12`, `1x12`, `combo` etc.).

---

## Contributing

If you encounter a Rocksmith+ key not in these tables, the easiest way to add it is:

1. Create a preset in AmpliTube 5 with the matching gear selected
2. Save it and open the `.at5p` file in a text editor
3. Extract the GUID from the relevant `Model=` attribute
4. Submit a PR adding the mapping to `rs_to_at5.py` and this document
