<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

definePage({
  meta: {
    public: true,
  },
})

const router = useRouter()

const goToRoleSelection = () => {
  router.push('/')
}

// 1. Reactive patient form matching your FastAPI Pydantic schema
const patientData = ref({
  sex: "M", 
  age: 65, 
  night_bed_exits: 0, 
  night_activity_duration_min: 0, 
  past_falls: 0, 
  mobility_score: 5, 
  high_risk_medication: 0, 
  cognitive_impairment: 0, 
  polypharmacy_count: 0, 
  orthostatic_hypotension: 0, 
  tug_seconds: 12.0, 
  days_since_last_fall: 0, 
  syncopal_fall: 0, 
  fall_cluster_30d: 0
})

const predictionResult = ref(null)
const limeExplanations = ref([])
const interventionResult = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')
const jwtToken = ref('')

const containsCjk = value => /[\u3400-\u9fff]/u.test(String(value ?? ''))

function englishText(value, fallback = '') {
  const text = String(value ?? '').trim()

  return text && !containsCjk(text) ? text : fallback
}

const suggestionFeatureLabels = {
  sex: 'Sex',
  age: 'Age',
  night_bed_exits: 'Night-time bed exits',
  night_activity_duration_min: 'Night-time activity duration',
  past_falls: 'Falls in the past year',
  mobility_score: 'Mobility score',
  high_risk_medication: 'Medicine linked to falls',
  cognitive_impairment: 'Cognitive impairment',
  polypharmacy_count: 'Number of medicines',
  orthostatic_hypotension: 'Postural hypotension',
  tug_seconds: 'Timed Up & Go (TUG)',
  days_since_last_fall: 'Time since the last fall',
  syncopal_fall: 'Fall with loss of consciousness',
  fall_cluster_30d: 'Two or more falls within 30 days',
}

// The current /predict response returns suggestion.items and a
// not_suggestion flag. Keep a legacy all_options fallback so older backend
// responses still render, rather than leaving the result panel blank.
const suggestionItems = computed(() => {
  const result = interventionResult.value
  if (!result || typeof result !== 'object')
    return []

  if (Array.isArray(result.items))
    return result.items

  return Array.isArray(result.all_options) ? result.all_options : []
})

const notSuggestedAge = computed(() => {
  const age = Number(patientData.value.age)

  return Number.isFinite(age)
    && age >= 75
    && age <= 100
})

function suggestionLabel(item) {
  const feature = String(item?.feature ?? '').toLowerCase()

  return englishText(item?.label, suggestionFeatureLabels[feature] || englishText(item?.feature, 'Care action'))
}

function suggestionAction(item) {
  const feature = suggestionLabel(item)
  const fallback = item?.can_flip
    ? `${feature} needs to change from ${item.from} to ${item.to}.`
    : `[Restricted] Altering '${feature}' alone is insufficient.`

  return englishText(item?.action, fallback)
}

function suggestionNote(value) {
  return englishText(value, 'No specific action matched this assessment. Continue baseline fall-prevention measures and confirm next steps with the nurse or clinician.')
}

function referenceTitle(reference) {
  return englishText(reference?.title, 'Evidence reference')
}

function priorityLabel(value) {
  return englishText(value, '')
}

function normalizeExplanations(items) {
  if (!Array.isArray(items))
    return []

  return items.map(item => {
    const feature = String(item?.feature ?? '').toLowerCase()
    const label = suggestionFeatureLabels[feature] || 'Assessment input'

    return {
      ...item,
      condition: englishText(item?.condition, `${label} condition`),
      direction: englishText(item?.direction, 'Model contribution'),
    }
  })
}

// 2. Authenticate and cache the Bearer token
const loginUser = async () => {
  try {
    const formData = new URLSearchParams()
    formData.append('username', 'admin_clinician')
    formData.append('password', 'password123')

    const response = await axios.post('http://localhost:8000/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    jwtToken.value = response.data.access_token
  } catch (err) {
    errorMessage.value = 'Authentication failed. Check backend connection.'
  }
}

// 3. Submit data to protected /predict endpoint
const submitAssessment = async () => {
  if (!jwtToken.value) {
    await loginUser()
  }
  if (!jwtToken.value) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await axios.post('http://localhost:8000/predict', patientData.value, {
      headers: { Authorization: `Bearer ${jwtToken.value}` }
    })
    predictionResult.value = response.data.fall_risk_level
    limeExplanations.value = normalizeExplanations(response.data.lime_explanations)
    interventionResult.value = response.data.suggestion || null
  } catch (err) {
    errorMessage.value = englishText(err.response?.data?.detail, 'Prediction request failed.')
  } finally {
    isLoading.value = false
  }
}

const featureSelector = ref(0) // Tracks selected axis highlights

// 11 feature strings 
const featureLabels = [
  'sex',
  'age',
  'night_bed_exits',
  'night_activity_duration_min',
  'past_falls',
  'mobility_score',
  'high_risk_medication',
  'cognitive_impairment',
  'polypharmacy_count',
  'orthostatic_hypotension',
  'tug_seconds', 
  'days_since_last_fall',
  'syncopal_fall',
  'fall_cluster_30d'
]

const radarDisplayLabels = {
  sex: 'SEX',
  age: 'AGE',
  night_bed_exits: 'BED EXITS',
  night_activity_duration_min: 'NIGHT ACTIVITY',
  past_falls: 'PAST FALLS',
  mobility_score: 'MOBILITY',
  high_risk_medication: 'HIGH-RISK MEDS',
  cognitive_impairment: 'COGNITION',
  polypharmacy_count: 'MED COUNT',
  orthostatic_hypotension: 'ORTHOSTATIC',
  tug_seconds: 'TUG SEC',
  days_since_last_fall: 'DAYS SINCE FALL',
  syncopal_fall: 'SYNCOPAL FALL',
  fall_cluster_30d: '30-DAY CLUSTER',
}

// Geometric Circular Symmetry Matrix (360° / 11 elements)
const angles = [
  0,
  (2 * Math.PI) / 14,
  (4 * Math.PI) / 14,
  (6 * Math.PI) / 14,
  (8 * Math.PI) / 14,
  (10 * Math.PI) / 14,
  (12 * Math.PI) / 14,
  (14 * Math.PI) / 14,
  (16 * Math.PI) / 14,
  (18 * Math.PI) / 14,
  (20 * Math.PI) / 14,
  (22 * Math.PI) / 14,
  (24 * Math.PI) / 14,
  (26 * Math.PI) / 14
]

const structuralData = computed(() => {
  // Fallback default array has exactly 11 elements to match our geometry structure perfectly
  if (!predictionResult.value || limeExplanations.value.length === 0) {
    return Array(14).fill(40) 
  }
  
  return featureLabels.map(label => {
    // Standardize underscores into clean spaces for text matching comparisons
    const cleanLabel = label.replace(/_/g, ' ').toLowerCase()
    
    // Check if the backend LIME condition string contains our structural clean name
    const match = limeExplanations.value.find(exp => {
      const cleanCondition = exp.condition.replace(/_/g, ' ').toLowerCase()
      return cleanCondition.includes(cleanLabel)
    })

    if (match) {
      const numericalMagnitude = Math.abs(match.weight)
      // Project the coefficient weight onto our 100px graphic limit boundary
      const dynamicPercentageRadius = Math.min(Math.max(numericalMagnitude * 220, 30), 100)
      return Math.round(dynamicPercentageRadius)
    }

    return 0 
  })
})

const radarPointsString = computed(() => {
  return structuralData.value.map((value, idx) => {
    const radius = value * 1.0
    const x = (radius * Math.sin(angles[idx])).toFixed(1)
    const y = (-radius * Math.cos(angles[idx])).toFixed(1)
    return `${x},${y}`
  }).join(' ')
})

const radarPointsArray = computed(() => {
  return structuralData.value.map((value, idx) => {
    return {
      x: (value * Math.sin(angles[idx])).toFixed(1),
      y: (-value * Math.cos(angles[idx])).toFixed(1),
      isActive: idx === featureSelector.value
    }
  })
})

const radarLabelsArray = computed(() => {
  const textRadius = 116 // Keep labels close to the plot while leaving a small safety margin at the sides
  return featureLabels.map((label, idx) => {
    const x = (textRadius * Math.sin(angles[idx])).toFixed(1)
    const y = (-textRadius * Math.cos(angles[idx])).toFixed(1)
    const fullName = label.replace(/_/g, ' ').toUpperCase()
    const name = radarDisplayLabels[label] || fullName
    
    let textAnchor = 'middle'
    if (parseFloat(x) > 15) textAnchor = 'start'
    if (parseFloat(x) < -15) textAnchor = 'end'

    return {
      name,
      x,
      y,
      textAnchor,
      fullName,
      isActive: idx === featureSelector.value
    }
  })
})

// Quick configuration helper tool to look up LIME direction vectors inside templates
const getFeatureDirection = (label) => {
  const cleanLabel = label.replace(/_/g, ' ').toLowerCase()
  const match = limeExplanations.value.find(exp => 
    exp.condition.replace(/_/g, ' ').toLowerCase().includes(cleanLabel)
  )
  return match ? match.direction : ''
}

onMounted(() => {
  console.log("14-Axis Structural Graphing Engine Activated Successfully.")
})

// Instantiate layout token refs matching the template definitions
const directionWrapperRef = ref(null)
const runnerAvatarRef = ref(null)
const humanPathRef = ref(null)
const speedBadgeRef = ref(null)

let trackPosition = 10
let movingForward = true
let currentSeconds = 12.0
let animationFrameId = null

const handleInput = (event) => {
  updateTugAnimation(event.target.value)
}

function updateTugAnimation(val) {
  let seconds = parseFloat(val)
  if (isNaN(seconds)) return
  
  if (seconds < 8.0) seconds = 8.0
  if (seconds > 31.9) seconds = 31.9
  currentSeconds = seconds

  // Safely verify DOM nodes exist before altering parameters
  if (!runnerAvatarRef.value || !humanPathRef.value || !speedBadgeRef.value) return

  if (seconds <= 10.0) {
    runnerAvatarRef.value.style.animationDuration = "0.25s"
    humanPathRef.value.setAttribute("fill", "#16a34a") 
    speedBadgeRef.value.innerText = "Fast Speed"
    speedBadgeRef.value.style.color = "#16a34a"
    speedBadgeRef.value.style.backgroundColor = "#f0fdf4"
  } else if (seconds <= 14.0) {
    runnerAvatarRef.value.style.animationDuration = "0.5s"
    humanPathRef.value.setAttribute("fill", "#2563eb") 
    speedBadgeRef.value.innerText = "Normal"
    speedBadgeRef.value.style.color = "#2563eb"
    speedBadgeRef.value.style.backgroundColor = "#eff6ff"
  } else {
    runnerAvatarRef.value.style.animationDuration = "1.1s"
    humanPathRef.value.setAttribute("fill", "#ef4444") 
    speedBadgeRef.value.innerText = "Slow"
    speedBadgeRef.value.style.color = "#ef4444"
    speedBadgeRef.value.style.backgroundColor = "#fff5f5"
  }
}

function driveAvatarLoop() {
  if (!directionWrapperRef.value) return

  let moveSpeed = (40 / currentSeconds)

  if (movingForward) {
    trackPosition += moveSpeed
    directionWrapperRef.value.style.transform = "scaleX(1)" 
    if (trackPosition >= 220) movingForward = false
  } else {
    trackPosition -= moveSpeed
    directionWrapperRef.value.style.transform = "scaleX(-1)" 
    if (trackPosition <= 10) movingForward = true
  }

  directionWrapperRef.value.style.left = trackPosition + "px"
  animationFrameId = requestAnimationFrame(driveAvatarLoop)
}

onMounted(() => {
  driveAvatarLoop()
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
})

</script>

<template>
  <div class="p-6 space-y-6 fall-risk-assessment">
    <div class="assessment-toolbar">
      <div class="assessment-toolbar__identity">
        <div class="assessment-toolbar__icon" aria-hidden="true">
          <VIcon icon="tabler-user-heart" size="22" />
        </div>
        <div>
          <div class="assessment-toolbar__eyebrow">FOR INDIVIDUALS · PERSONAL USE</div>
          <h1>Personal Fall Risk Assessment</h1>
          <p>Enter your details to receive an AI risk level and actionable guidance</p>
        </div>
      </div>
      <button
        type="button"
        class="assessment-toolbar__back"
        aria-label="Back to role selection"
        @click="goToRoleSelection"
      >
        <VIcon icon="tabler-arrow-left" size="18" />
        Back to role selection
      </button>
    </div>
    
    <!-- Input Form Grid -->
    <div class="assessment-layout">

      <!-- Main Container Box -->
      <div class="assessment-form-card" style="width: 800px; margin: 0 auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        
        <!-- Header Title -->
        <header style="text-align: center; margin-bottom: 25px; border-bottom: 2px solid #334155; padding-bottom: 10px;">
          <h1 style="font-size: 1.75rem; font-weight: 700; margin: 0; color: #0f172a;">Fall Risk Assessment</h1>
        </header>

        <!-- Patient Demographics Section -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;">
          <div>
            <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">Sex:</label>
            <div style="display: flex; gap: 16px; align-items: center; width: 100%; padding: 8px; border: 1px solid rgb(203, 213, 225); border-radius: 4px; box-sizing: border-box;">
              <label for="sex1" style="display: flex; align-items: center; gap: 6px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.sex" type="radio" name="pSex" value="M" id="sex1" style="margin: 0; cursor: pointer;" class="border p-2 w-full rounded">
                <span>Male</span>
              </label>
              <label for="sex2" style="display: flex; align-items: center; gap: 6px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.sex" type="radio" name="pSex" value="F" id="sex2" style="margin: 0; cursor: pointer;" class="border p-2 w-full rounded">
                <span>Female</span>
              </label>
            </div>
          </div>
          <div>
            <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">Age:</label>
            <input v-model.number="patientData.age" type="number" min="60" max="100" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
          </div>
        </div>

        <!-- Dynamic Form Section -->
            
        <!-- 1. Recent Falls Section -->
        <div style="border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
          <div style="background-color: #f8fafc; padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #cbd5e1;">Recent Falls</div>
            <div style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="0" class="border p-2 w-full rounded"> None (Score: 0)
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="1" class="border p-2 w-full rounded"> One (Score: 1)
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="2" class="border p-2 w-full rounded"> Two (Score: 2)
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="3" class="border p-2 w-full rounded"> Three (Score: 3)
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="4" class="border p-2 w-full rounded"> Four (Score: 4)
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.past_falls" type="radio" name="recentFalls" value="5" class="border p-2 w-full rounded"> Five (Score: 5)
              </label>
              <label class="assessment-days-since-fall" style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.days_since_last_fall" type="number" name="daysSinceLastFall" min="0" value="0" class="border p-2 w-full rounded"> days since last fall
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.syncopal_fall" type="checkbox" name="syncopalFall" :true-value="1" :false-value="0" class="border p-2 w-full rounded"> historical event: syncopal fall
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                <input v-model.number="patientData.fall_cluster_30d" type="checkbox" name="fallCluster30d" :true-value="1" :false-value="0" class="border p-2 w-full rounded"> Whether you have a dangerous pattern of multiple falls grouped closely together within a tight 30-day window.
              </label>
            </div>
          </div>

          <!-- 2. Mobility Score Section -->
          <div style="border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
            <div style="background-color: #f8fafc; padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #cbd5e1;">
              Mobility Score <span style="font-weight: 400; font-size: 0.8rem; color: #64748b;"><br><ul><li>Low range ratings (scores 1–4) catch severe physical instability, where you cannot walk alone and requires constant one-on-one help.</li><li>Mid-range ratings (scores 5–7) typically signify a reliance on assistive devices, such as walking sticks, quad-canes, or wheeled frames, to walk safely.</li><li>High-range ratings (scores 8–10) represent mild unsteadiness, where you can walk independently.</li></ul></span>
            </div>
            <div style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
              <input v-model.number="patientData.mobility_score" type="number" min="1" max="10" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
            </div>
          </div>

          <!-- 3. tug_seconds Section -->
          <div style="margin: 40px auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">

            <!-- TUG Input Group with Integrated Animation Canvas -->
            <div style="display: flex; flex-direction: column; gap: 8px;">
              <label for="pTUG" style="font-size: 0.9rem; font-weight: 600; color: #334155;">
                TUG Seconds (8.0 - 31.9)
              </label>
                      
              <div style="display: flex; align-items: center; gap: 16px;">
                <!-- Numeric Input Box linked via Vue reference -->
                <input 
                  v-model.number="patientData.tug_seconds" 
                  type="number" 
                  id="pTUG" 
                  min="8.0" 
                  max="31.9" 
                  step="0.1" 
                  value="12.0" 
                  @input="handleInput"
                  style="width: 100px; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 1rem; text-align: center; outline: none;" 
                  class="border p-2 w-full rounded" 
                >
                          
                <!-- MINI ANIMATION FRAME CONTAINER -->
                <div style="flex-grow: 1; height: 54px; border: 1px solid #e2e8f0; border-radius: 6px; background-color: #f8fafc; position: relative; overflow: hidden; display: flex; align-items: center;">
                              
                  <!-- Track Line Graphic -->
                  <div style="position: absolute; left: 10px; right: 10px; height: 2px; background-color: #cbd5e1; bottom: 8px;"></div>
                              
                    <!-- Ref tag added to handle moving position and turn flipping -->
                    <div ref="directionWrapperRef" id="directionWrapper" style="position: absolute; left: 10px; bottom: 8px; width: 32px; height: 32px; transition: left 0.1s linear;">
                      <!-- Ref tag added to handle gait animation speeds -->
                      <div ref="runnerAvatarRef" id="runnerAvatar" class="gait-loop" style="width: 100%; height: 100%; transform-origin: center bottom;">
                        <svg viewBox="0 -1000 1000 1000" width="100%" height="100%">
                          <!-- Ref tag added to handle color updates -->
                          <path ref="humanPathRef" id="humanPath" fill="#2563eb" d="m320-40-48-36 104-139-8-191q-2-52 5.5-109.5T397-617l-97 56v111h-60v-146l167-96q17-10 32.5-15t29.5-5q27 0 48.5 21t41.5 66q20 46 59 75.5t94 46.5q7-4 13.5-5.5T739-510q23 0 42 18.5t19 41.5v410h-30v-410q0-12-9-21t-21-9q-12 0-21 9t-9 21v30h-30v-33q-42-11-87.5-42T521-568q-12 34-18.5 75t-4.5 73l97 137v243h-60v-219l-85-95-10 154L320-40Zm218-714q-30 0-51.5-21.5T465-827q0-30 21.5-51.5T538-900q30 0 51.5 21.5T611-827q0 30-21.5 51.5T538-754Z"/>
                        </svg>
                      </div>
                    </div>

                    <!-- Ref tag added to handle text badge values -->
                    <div ref="speedBadgeRef" id="speedBadge" style="position: absolute; right: 10px; top: 14px; font-size: 0.75rem; font-weight: 700; color: #2563eb; background-color: #eff6ff; padding: 2px 8px; border-radius: 12px; text-transform: uppercase;">
                      Normal
                    </div>
                  </div>
                </div>

                <span style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">
                  Time taken to stand up, walk 3 metres, turn around, walk back, and sit down.
                </span>
              </div>
            </div>

            <!-- 4. Night Bed Exits and Night Activity Duration Section -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;">
              <div>
                <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">Night Bed Exits (0-8):</label>
                <input v-model.number="patientData.night_bed_exits" type="number" min="0" max="8" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
              </div>
              <div>
                <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">Night Activity Duration (min):</label>
                <input v-model.number="patientData.night_activity_duration_min" type="number" min="0" value="0" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
              </div>
            </div>

            <!-- 5. High Risk Medication and Polypharmacy Count Section -->
            <div style="border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
              <div style="background-color: #f8fafc; padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #cbd5e1;">
                Medications <span style="font-weight: 400; font-size: 0.8rem; color: #64748b;">(Anti-depressants, anti-hypertensives, sedatives, anti-Parkinson's, diuretics, hypnotics)</span>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;">
                <div>
                  <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">High Risk Medication:</label>
                  <input v-model.number="patientData.high_risk_medication" type="checkbox" :true-value="1" :false-value="0" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
                </div>
                <div>
                  <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 4px;">Polypharmacy Count (0-14):</label>
                  <input v-model.number="patientData.polypharmacy_count" type="number" min="0" max="14" value="0" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
                </div>
              </div>
            </div>

            <!-- 6. Cognitive Status Section -->
            <div style="border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
              <div style="background-color: #f8fafc; padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #cbd5e1;">
                Cognitive Status <span style="font-weight: 400; font-size: 0.8rem; color: #64748b;">(Hodkinson Abbreviated Mental Test Score - AMTS)</span>
              </div>
              <div style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                  <input v-model.number="patientData.cognitive_impairment" type="radio" name="cognitiveStatus" value="0" class="border p-2 w-full rounded"> AMTS 9-10 (Score: 0)
                </label>
                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                  <input v-model.number="patientData.cognitive_impairment" type="radio" name="cognitiveStatus" value="0" class="border p-2 w-full rounded"> AMTS 7-8 (Score: 0)
                </label>
                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                  <input v-model.number="patientData.cognitive_impairment" type="radio" name="cognitiveStatus" value="1" class="border p-2 w-full rounded"> AMTS 5-6 (Score: 1)
                </label>
                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
                  <input v-model.number="patientData.cognitive_impairment" type="radio" name="cognitiveStatus" value="2" class="border p-2 w-full rounded"> AMTS 4 or less (Score: 2)
                </label>
              </div>
            </div>

            <!-- 7. Orthostatic Hypotension Section -->
            <div style="border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
              <div style="background-color: #f8fafc; padding: 10px 14px; font-weight: 700; border-bottom: 1px solid #cbd5e1;">
                Orthostatic Hypotension <span style="font-weight: 400; font-size: 0.8rem; color: #64748b;">(causes dizziness, lightheadedness, and sometimes fainting when you stand up from a sitting or lying position.)</span>
              </div>
              <div style="padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                <input v-model.number="patientData.orthostatic_hypotension" type="checkbox" :true-value="1" :false-value="0" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" class="border p-2 w-full rounded">
              </div>
            </div>
          </div>

          <div class="assessment-side-rail">
          <div class="assessment-actions-panel" style="width: 600px; border: 1px solid #cbd5e1; border-radius: 8px; ">
            <div class="grid grid-cols-2 gap-4 bg-white p-6 rounded shadow">
              <div class="col-span-2 mt-4">
                <button @click="submitAssessment" :disabled="isLoading" class="assessment-submit bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  {{ isLoading ? 'Processing...' : 'Run Assessment & LIME XAI' }}
                </button>
              </div>
              <p v-if="errorMessage" class="assessment-error text-red-500 col-span-2">{{ errorMessage }}</p>
            </div>

            <!-- Results Panel -->
            <div v-if="predictionResult" class="assessment-result-panel bg-gray-50 p-6 rounded border shadow-inner space-y-4">
              <h3 class="text-lg font-semibold">Prediction Result: <span class="text-blue-600 font-bold">{{ predictionResult }}</span></h3>
              
              <h4 class="font-medium text-gray-700">LIME Local Feature Explanations:</h4>
              <ul class="list-disc pl-5 space-y-1">
                <li v-for="(item, index) in limeExplanations" :key="index">
                  <span class="font-mono font-semibold">{{ item.condition }}</span> — Weight: {{ item.weight }} 
                  <span class="text-gray-500 text-sm">({{ item.direction }})</span>
                </li>
              </ul>
            </div>
	
	          <!-- Results Panel -->
            <div v-if="predictionResult" class="assessment-result-panel bg-gray-50 p-6 rounded border shadow-inner space-y-4">
              <h3 class="text-lg font-semibold">Suggestions: </h3>
      
	            <!-- CASE A: Patient is NOT High Risk (Outputs the simple text note) -->
            <!-- Ages 75–100 are intentionally outside this page's suggestion scope. -->
            <div v-if="notSuggestedAge" class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded p-3">
              <div class="font-semibold">Not suggested（75–100 岁）</div>
              <div class="mt-1">This page provides caregiver suggestions only for residents aged 60–74. Follow the facility’s standard fall-assessment process and confirm next steps with the nurse or clinician.</div>
            </div>

            <!-- Render the evidence-backed suggestion.items returned by /predict. -->
            <div v-else-if="suggestionItems.length" class="space-y-2">
              <h4 class="font-medium text-gray-700 border-b pb-2">Care actions for this assessment:</h4>

              <ul class="list-disc pl-5 space-y-2">
                <li v-for="(item, index) in suggestionItems" :key="item.feature || index" class="text-sm text-gray-800">
                  <span class="font-semibold">{{ suggestionLabel(item) }}</span>
                  <span class="text-gray-700"> — {{ suggestionAction(item) }}</span>
                  <span v-if="priorityLabel(item.priority_label)" class="ml-1 text-xs text-gray-500">({{ priorityLabel(item.priority_label) }})</span>
                  <span v-if="Array.isArray(item.references) && item.references.length" class="block text-xs text-blue-700 mt-1">
                    Evidence:
                    <a
                      v-for="reference in item.references"
                      :key="reference.id || reference.url"
                      :href="reference.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="underline mr-2"
                    >
                      {{ referenceTitle(reference) }}
                    </a>
                  </span>
                </li>
              </ul>
            </div>

            <!-- Keep the previous short fallback for records with no matched action. -->
            <div v-else class="text-sm text-blue-700 italic">
              {{ suggestionNote(interventionResult?.note) }}
            </div>
          </div>

      </div>
    <!-- Right Side SVG Canvas Area (Occupies the second column on wide screens) -->
    <div class="assessment-radar-card flex justify-center items-center p-6 bg-slate-950 rounded-lg border border-slate-900 shadow-inner min-h-[390px] w-full overflow-visible">
      
      <!-- Expanded grid margins from 360 to 450 to accommodate long multi-word labels cleanly -->
      <svg width="100%" height="340" viewBox="-200 -160 400 320" class="overflow-visible select-none">
        <g class="radar-plot" transform="scale(1.3)">
        <!-- Grid Spoke Axis Lines -->
        <line v-for="(angle, idx) in angles" :key="'spoke-'+idx" x1="0" y1="0" :x2="100 * Math.sin(angle)" :y2="-100 * Math.cos(angle)" stroke="#1e293b" stroke-width="1.25" />
        
        <!-- Concentric circle guidelines -->
        <circle cx="0" cy="0" r="25" fill="none" stroke="#0f172a" stroke-width="1" />
        <circle cx="0" cy="0" r="50" fill="none" stroke="#1e293b" stroke-width="0.75" stroke-dasharray="3" />
        <circle cx="0" cy="0" r="75" fill="none" stroke="#1e293b" stroke-width="0.75" stroke-dasharray="3" />
        <circle cx="0" cy="0" r="100" fill="none" stroke="#334155" stroke-width="1.5" />
        
        <!-- Dynamic Vector Patient Polygon Underlay -->
        <polygon :points="radarPointsString" fill="rgba(255, 255, 255, 0.012)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1" stroke-dasharray="4" />

        <!-- Dynamic Spoke Lines -->
        <line v-for="(angle, idx) in angles" :key="'fill-spoke-'+idx" x1="0" y1="0" :x2="radarPointsArray[idx]?.x" :y2="radarPointsArray[idx]?.y" :stroke="getFeatureDirection(featureLabels[idx]).includes('push') ? '#ef4444' : '#10b981'" stroke-width="2.25" stroke-linecap="round" />
        
        <!-- Dynamic Joint Nodes -->
        <circle v-for="(pt, idx) in radarPointsArray" :key="'node-'+idx" :cx="pt.x" :cy="pt.y" :r="pt.isActive ? 7 : 4" :fill="getFeatureDirection(featureLabels[idx]).includes('push') ? '#ef4444' : '#10b981'" stroke="#090d16" stroke-width="1.5" />

        </g>

        <!-- Fixed Axis Text Labels (14 total elements looping smoothly) -->
        <text
          v-for="(lbl, idx) in radarLabelsArray" :key="'label-'+idx" :x="lbl.x" :y="lbl.y" :text-anchor="lbl.textAnchor" dominant-baseline="central"
          :aria-label="lbl.fullName"
          :fill="getFeatureDirection(featureLabels[idx]).includes('push') ? '#fb7185' : '#34d399'"
          :class="[
            'text-[9px] transition-all duration-300 font-bold',
            lbl.isActive ? 'font-black scale-110' : '', 
            getFeatureDirection(featureLabels[idx]).includes('push') ? 'fill-rose-400 font-bold' : 'fill-emerald-400 font-bold'
          ]"
        >
          <title>{{ lbl.fullName }}</title>
          {{ lbl.name }}
        </text>
      </svg>
    
    </div>

    </div>

    </div>

  </div>

</template>

<style>
/* Staggered entrance for list cards */
@keyframes slideUpFade {
  0% { opacity: 0; transform: translateY(15px); filter: blur(2px); }
  100% { opacity: 1; transform: translateY(0); filter: blur(0); }
}

/* Pulse warning glow for High-Risk states */
@keyframes criticalGlow {
  0% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(244, 63, 94, 0); }
  100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); }
}

/* Pulse success glow for Low-Risk state shields */
@keyframes safeGlow {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.animate-fade-up {
  animation: slideUpFade 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.pulse-risk-high {
  animation: criticalGlow 2s infinite;
}

.pulse-risk-low {
  animation: safeGlow 2s infinite;
}

/* Smooth morphing transitions for the SVG polygon shape */
polygon, line, circle {
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>

<style scoped>
.fall-risk-assessment {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-inline-size: 1480px;
  margin-inline: auto;
}

.assessment-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 22px;
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  border-radius: 16px;
  background:
    linear-gradient(120deg, rgba(var(--v-theme-primary), 0.11), rgba(var(--v-theme-info), 0.04)),
    rgb(var(--v-theme-surface));
  box-shadow: 0 8px 24px rgba(var(--v-theme-on-background), 0.04);
}

.assessment-toolbar__identity {
  display: flex;
  align-items: center;
  gap: 14px;
}

.assessment-toolbar__icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  inline-size: 46px;
  block-size: 46px;
  border-radius: 13px;
  background: rgba(var(--v-theme-primary), 0.13);
  color: rgb(var(--v-theme-primary));
}

.assessment-toolbar__eyebrow {
  color: rgb(var(--v-theme-primary));
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.1em;
}

.assessment-toolbar h1 {
  margin: 3px 0 2px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 1.15rem;
  font-weight: 700;
}

.assessment-toolbar p {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.62);
  font-size: 0.8rem;
}

.assessment-toolbar__back {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  min-block-size: 40px;
  padding: 0 15px;
  border: 1px solid rgba(var(--v-theme-primary), 0.25);
  border-radius: 10px;
  background: rgba(var(--v-theme-primary), 0.07);
  color: rgb(var(--v-theme-primary));
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 650;
  transition: background 180ms ease, transform 180ms ease;
}

.assessment-toolbar__back:hover {
  background: rgba(var(--v-theme-primary), 0.14);
  transform: translateX(-2px);
}

.assessment-toolbar__back:focus-visible {
  outline: 3px solid rgba(var(--v-theme-primary), 0.28);
  outline-offset: 2px;
}

@media (max-width: 700px) {
  .assessment-toolbar {
    align-items: flex-start;
    flex-direction: column;
    padding: 17px;
  }

  .assessment-toolbar__back {
    inline-size: 100%;
    justify-content: center;
  }
}
</style>
<style>
@keyframes customGaitWalk {
    0% { transform: scale(1, 1); }
    50% { transform: scale(0.94, 1.06) skewX(-4deg); }
    100% { transform: scale(1, 1); }
}
.gait-loop {
    animation: customGaitWalk 0.5s infinite ease-in-out;
}
</style>
<style scoped>
/* Suggestions Container Context block */
.section-container {
    width: 100%;
    max-width: 600px;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0px 1px 3px rgba(16, 24, 40, 0.05), 0px 12px 42px rgba(16, 24, 40, 0.04);
}

.section-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #0f172a;
    margin-bottom: 14px;
}

.suggestions-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* Suggestion Card with Slide/Fade Micro-Animation Trigger */
.suggestion-item-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
    line-height: 1.45;
    color: #334155;
    
    /* Animation implementation properties */
    opacity: 0;
    transform: translateY(8px) scale(0.99);
    animation: staggerFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.suggestion-bullet {
    color: #2563eb; /* Clean blue feature anchor color */
    font-weight: bold;
    font-size: 0.9rem;
    line-height: 1;
    margin-top: 1px;
}

/* Performance Keyframe Track for smooth fade-in arrival */
@keyframes staggerFadeIn {
    0% {
        opacity: 0;
        transform: translateY(8px) scale(0.99);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
</style>

<style scoped>
.assessment-layout {
  display: grid !important;
  grid-template-columns: minmax(0, 1.15fr) minmax(380px, 0.85fr);
  align-items: start;
  gap: 20px;
}

.assessment-form-card,
.assessment-actions-panel {
  box-sizing: border-box;
  inline-size: auto !important;
  min-inline-size: 0;
  margin: 0 !important;
}

.assessment-form-card {
  grid-column: 1;
  background: rgb(var(--v-theme-surface));
}

.assessment-side-rail {
  display: flex;
  grid-column: 2;
  flex-direction: column;
  align-self: start;
  gap: 20px;
  min-inline-size: 0;
  position: sticky;
  top: 20px;
}

.assessment-actions-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: rgba(var(--v-theme-surface), 0.78);
}

.assessment-actions-panel > .grid {
  flex: 0 0 auto;
  padding: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.assessment-side-rail > * {
  min-inline-size: 0;
}

.assessment-side-rail .section-container {
  box-sizing: border-box;
  inline-size: 100%;
  max-inline-size: none;
  margin-top: 0 !important;
}

.assessment-submit {
  display: inline-flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  min-block-size: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-info)));
  color: #fff;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
}

.assessment-submit:hover:not(:disabled) {
  box-shadow: 0 8px 18px rgba(var(--v-theme-primary), 0.25);
  transform: translateY(-1px);
}

.assessment-submit:disabled {
  cursor: wait;
  opacity: 0.62;
}

.assessment-submit:focus-visible {
  outline: 3px solid rgba(var(--v-theme-primary), 0.3);
  outline-offset: 2px;
}

.assessment-error {
  margin: 0;
  color: rgb(var(--v-theme-error));
  font-size: 0.8rem;
  line-height: 1.5;
}

.assessment-result-panel {
  margin: 0 !important;
  border-color: rgba(var(--v-theme-primary), 0.16) !important;
  background: rgba(var(--v-theme-primary), 0.045) !important;
  color: rgb(var(--v-theme-on-surface));
  overflow-wrap: anywhere;
}

.assessment-radar-card {
  align-self: start;
  inline-size: 100%;
  min-block-size: 330px;
  box-sizing: border-box;
  border-radius: 14px;
  background: #0b1526;
}

.assessment-radar-card svg {
  display: block;
  block-size: 300px;
  max-inline-size: 100%;
}

.assessment-radar-card text {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  paint-order: stroke fill;
  stroke: rgba(11, 21, 38, 0.75);
  stroke-width: 1.25px;
}

.assessment-form-card ul {
  margin: 6px 0 0;
  padding-inline-start: 18px;
  line-height: 1.45;
}

.assessment-form-card input[type='checkbox'] {
  inline-size: 16px !important;
  block-size: 16px;
  padding: 0 !important;
  flex: 0 0 auto;
}

.assessment-form-card input[type='radio'] {
  flex: 0 0 auto;
}

@media (max-width: 1050px) {
  .assessment-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .assessment-form-card,
  .assessment-side-rail {
    grid-column: auto;
  }

  .assessment-side-rail {
    position: static;
  }

  .assessment-radar-card {
    min-block-size: 330px;
  }
}

@media (max-width: 700px) {
  .assessment-layout {
    gap: 14px;
  }

  .fall-risk-assessment {
    gap: 14px;
    padding: 14px !important;
  }

  .assessment-form-card {
    padding: 18px !important;
  }

  .assessment-form-card > header h1 {
    font-size: 1.45rem !important;
    line-height: 1.25;
  }

  .assessment-radar-card {
    min-block-size: 285px;
    padding: 8px !important;
  }

  .assessment-radar-card svg {
    block-size: 260px;
  }

  .assessment-form-card > div[style*='display: flex'] {
    flex-wrap: wrap;
  }

  .assessment-form-card [name='daysSinceLastFall'] {
    inline-size: 108px !important;
  }

  .assessment-days-since-fall {
    gap: 2px !important;
  }

  .assessment-form-card [style*='grid-template-columns: 1fr 1fr'] {
    grid-template-columns: 1fr !important;
  }

  .assessment-radar-card text {
    font-size: 10px;
    stroke-width: 1px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .assessment-submit,
  .assessment-toolbar__back {
    transition: none;
  }
}
</style>
