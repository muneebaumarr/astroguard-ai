export const vitalFields = [
  { key: 'heart_rate', label: 'Heart rate', unit: 'bpm', min: 0 },
  { key: 'blood_pressure_systolic', label: 'Systolic pressure', unit: 'mmHg', min: 0 },
  { key: 'blood_pressure_diastolic', label: 'Diastolic pressure', unit: 'mmHg', min: 0 },
  { key: 'blood_glucose', label: 'Blood glucose', unit: 'mg/dL', min: 0 },
  { key: 'body_temperature', label: 'Body temperature', unit: 'degC' },
  { key: 'spo2', label: 'Blood oxygen (SpO₂)', unit: '%', min: 0, max: 100 },
]

export function initialForm() {
  const now = new Date().toISOString()
  return { checkin_date: now.slice(0, 10), observation_time: now.slice(11, 16), context: 'resting',
    ...Object.fromEntries(vitalFields.map(field => [field.key, ''])),
    sleep_hours: '', mood: '', stress: '', exercise_minutes: '', symptoms: '', notes: '' }
}

export function validateCheckin(form) {
  const errors = {}
  const observed = `${form.checkin_date}T${form.observation_time}:00Z`
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.checkin_date)) errors.checkin_date = 'Choose a UTC check-in date.'
  if (!/^\d{2}:\d{2}$/.test(form.observation_time) || Number.isNaN(Date.parse(observed))) errors.observation_time = 'Enter a valid UTC observation time.'
  if (!['resting', 'exercise', 'recovery', 'unspecified'].includes(form.context)) errors.context = 'Choose an observation context.'
  const readings = []
  for (const field of vitalFields) {
    if (form[field.key] === '') continue
    const value = Number(form[field.key])
    if (!Number.isFinite(value) || (field.min !== undefined && value < field.min) || (field.max !== undefined && value > field.max)) {
      errors[field.key] = field.max !== undefined ? `Enter a value from ${field.min} to ${field.max}.` : 'Enter a valid value within the input limits.'
    } else readings.push({ indicator: field.key, value, unit: field.unit })
  }
  const hasSystolic = form.blood_pressure_systolic !== ''
  const hasDiastolic = form.blood_pressure_diastolic !== ''
  if (hasSystolic !== hasDiastolic) {
    errors[hasSystolic ? 'blood_pressure_diastolic' : 'blood_pressure_systolic'] = 'Enter both blood pressure components.'
  } else if (hasSystolic && Number(form.blood_pressure_systolic) <= Number(form.blood_pressure_diastolic)) {
    errors.blood_pressure_systolic = 'Systolic pressure must exceed diastolic pressure.'
  }
  const body = { checkin_date: form.checkin_date, observed_at: observed, context: form.context, readings }
  for (const [key, min, max, integer] of [['sleep_hours', 0, 24, false], ['mood', 1, 5, true], ['stress', 1, 5, true], ['exercise_minutes', 0, 1440, true]]) {
    if (form[key] === '') continue
    const value = Number(form[key])
    if (!Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) {
      errors[key] = `Enter ${integer ? 'a whole number' : 'a value'} from ${min} to ${max}.`
    } else body[key] = value
  }
  body.symptoms = form.symptoms.split('\n').map(value => value.trim()).filter(Boolean)
  if (body.symptoms.length > 20 || body.symptoms.some(value => value.length > 100)) errors.symptoms = 'Use up to 20 symptoms, each 100 characters or fewer.'
  if (form.notes.length > 2000) errors.notes = 'Use 2,000 characters or fewer.'
  if (form.notes.trim()) body.notes = form.notes.trim()
  if (!readings.length && !body.symptoms.length && !body.notes && !['sleep_hours', 'mood', 'stress', 'exercise_minutes'].some(key => key in body)) {
    errors.form = 'Record at least one measurement, wellness value, symptom or note.'
  }
  return { body, errors }
}

export function validationErrors(error, body) {
  const errors = {}
  for (const [path, message] of Object.entries(error.details || {})) {
    const parts = path.split('.')
    if (parts[0] !== 'body') continue
    const key = parts[1] === 'readings' ? body.readings[Number(parts[2])]?.indicator : parts[1]
    if (key) errors[key] = message
  }
  return { ...errors, form: error.message }
}
