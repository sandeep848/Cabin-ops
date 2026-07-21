# CabinOps AI Dataset Card

This dataset is designed for training and evaluating intent classification, slot extraction, and cabin routing models in a simulated in-flight crew assistance system.

## Dataset Summary

The dataset consists of passenger-facing requests (utterances) mapped to flight operation metadata, predicted intents, priority metrics, and appropriate flight phase routing rules.

## Schema & Columns

| Column | Type | Description |
|---|---|---|
| `utterance_text` | Text | The raw text input from the passenger (via text or speech translation). |
| `input_modality` | Categorical | The mode of entry: `text`, `voice`, or `quick_button`. |
| `seat` | Text | The seat location of the passenger (e.g., `22A`). |
| `flight_phase` | Categorical | The current phase of the flight: `cruise`, `takeoff`, or `landing_preparation`. |
| `intent` | Categorical | The parsed intent. Possible values: `medical_assistance`, `emergency`, `allergy_question`, `meal_request`, `water_request`, `blanket_request`, `screen_issue`, `missed_announcement`, `out_of_scope`. |
| `urgency` | Categorical | Priority label assigned: `high`, `medium`, `low`, or `none`. |
| `crew_required` | Boolean | Whether this request requires dispatching a physical crew member. |
| `expected_action` | Text | Summary of the action that the system is expected to perform. |

## Target Intents

1. **medical_assistance**: Health symptoms, dizzy, nauseous, pain, sickness.
2. **emergency**: Direct safety threats, smoke, fire.
3. **allergy_question**: Inquiries regarding food content or restrictions (e.g. nuts, dairy).
4. **meal_request**: Food, snacks, drinks, tea, coffee.
5. **water_request**: Plain water requests.
6. **blanket_request**: Pillows, blankets, headphones, comfort items.
7. **screen_issue**: Frozen IFE screens, touch issues.
8. **missed_announcement**: Captain announcements, turbulence updates.
9. **out_of_scope**: Irrelevant queries (e.g. hotel booking, weather).

## Usage & Limitations

This dataset is designed for prototyping and rule-based or small classifier model benchmarking. It represents simulated in-flight scenarios and should not be used as is in critical safety-of-life operations without human-in-the-loop validation.
