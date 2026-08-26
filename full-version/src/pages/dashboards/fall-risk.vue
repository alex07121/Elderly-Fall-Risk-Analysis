<script setup>
import { ref } from 'vue'
import axios from 'axios'

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
    limeExplanations.value = response.data.lime_explanations
	  interventionResult.value = response.data.suggestion || null
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Prediction request failed.'
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
  const textRadius = 140 // Slightly wider radius spacing to separate tighter 14-axis labels
  return featureLabels.map((label, idx) => {
    const x = (textRadius * Math.sin(angles[idx])).toFixed(1)
    const y = (-textRadius * Math.cos(angles[idx])).toFixed(1)
    
    let textAnchor = 'middle'
    if (parseFloat(x) > 15) textAnchor = 'start'
    if (parseFloat(x) < -15) textAnchor = 'end'

    return {
      name: label.replace(/_/g, ' ').toUpperCase(),
      x,
      y,
      textAnchor,
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

import { computed, onMounted, onUnmounted } from 'vue'

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
  <div class="p-6 space-y-6">
    
    <!-- Input Form Grid -->
    <div style="display: flex;">

      <!-- Main Container Box -->
      <div style="width: 800px; margin: 0 auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        
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
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer;">
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

          <div style="width: 600px; border: 1px solid #cbd5e1; border-radius: 8px; ">
            <div class="grid grid-cols-2 gap-4 bg-white p-6 rounded shadow">
              <div class="col-span-2 mt-4">
                <button @click="submitAssessment" :disabled="isLoading" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  {{ isLoading ? 'Processing...' : 'Run Assessment & LIME XAI' }}
                </button>
              </div>
              <p v-if="errorMessage" class="text-red-500 col-span-2">{{ errorMessage }}</p>
            </div>

            <!-- Results Panel -->
            <div v-if="predictionResult" class="bg-gray-50 p-6 rounded border shadow-inner space-y-4">
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
            <div v-if="predictionResult" class="bg-gray-50 p-6 rounded border shadow-inner space-y-4">
              <h3 class="text-lg font-semibold">Suggestions: </h3>
      
	            <!-- CASE A: Patient is NOT High Risk (Outputs the simple text note) -->
	            <div v-if="predictionResult !== 'HIGH' || !interventionResult" class="text-sm text-blue-700 italic">
		            {{ interventionResult?.note || "Patient is not classified as HIGH risk. Baseline safety precautions are sufficient." }}
	            </div>

	            <!-- CASE B: Patient IS High Risk (Loops through all options natively using HTML tags) -->
	            <div v-else class="space-y-2">
		            <h4 class="font-medium text-gray-700 border-b pb-2">Required Patient Alteration Guide:</h4>
		
		            <ul class="list-disc pl-5 space-y-2">
		              <li v-for="(item, index) in interventionResult.all_options" :key="index" class="text-sm text-gray-800">
			
                    <!-- Render this segment if the individual clinical feature can flip the risk level -->
                    <template v-if="item.can_flip">
                      <span class="font-mono font-bold text-red-700">{{ item.feature }}</span> 
                      need to change from <span class="font-semibold">{{ item.from }}</span> 
                      to <span class="text-emerald-600 font-bold">{{ item.to }}</span>.
                    </template>
        
                    <!-- Render this fallback segment if the single feature adjustment is insufficient -->
                    <template v-else>
                      <span class="text-gray-400 italic">
                      [Restricted] Altering '<span class="font-mono font-medium">{{ item.feature }}</span>' alone is insufficient.
                      </span>
                    </template>
		              </li>
		            </ul>
	            </div>
          </div>

          <!-- Extracted AI Suggestions Module -->
          <div v-if="predictionResult" class="section-container mt-6">
            <h3 class="section-title">AI Real-Time Proactive Suggestions</h3>
            
            <div id="suggestionsWrapper" class="suggestions-container">
              
              <!-- CASE A: Critical Baseline Lockout (Age 85, Falls 5 Case) -->
              <div 
                v-if="interventionResult?.all_options && !interventionResult.all_options.some(o => o.can_flip)"
                class="suggestion-item-card" 
                style="animation-delay: 0ms; border-left: 3px solid #ef4444;"
              >
                <span class="suggestion-bullet" style="color: #ef4444;">⚠️</span>
                <p>
                  <strong>Multi-Disciplinary Care Required:</strong> Patient's unchangeable baseline profile parameters (Age / Past Falls) are mathematically dominant. Alleviating single modifiable attributes independently is completely insufficient to change the prediction. Immediate comprehensive clinical triage protocol required.
                </p>
              </div>
          
              <!-- CASE B: Actionable Variable Intervention Paths Open -->
              <template v-else>
                <div 
                  v-for="(item, idx) in interventionResult?.all_options" 
                  :key="idx"
                  v-show="item.can_flip"
                  class="suggestion-item-card" 
                  :style="{ animationDelay: (idx * 100) + 'ms' }"
                >
                  <span class="suggestion-bullet">✦</span>
                  <p>
                    Optimize modifiable metric <strong style="color: #2563eb; text-transform: uppercase;">{{ item.feature.replace(/_/g, ' ') }}</strong>: 
                    Reduce score value from <span style="font-weight: 600;">{{ item.from }}</span> 
                    down to a target threshold of <span style="color: #10b981; font-weight: 700;">{{ item.to }}</span> to successfully flip the prediction model and lower the global risk level.
                  </p>
                </div>
              </template>

            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Side SVG Canvas Area (Occupies 3 columns in tailwind) -->
    <div class="lg:col-span-3 flex justify-center items-center p-6 bg-slate-950 rounded-lg border border-slate-900 shadow-inner min-h-[390px] w-full overflow-visible">
      
      <!-- Expanded grid margins from 360 to 450 to accommodate long multi-word labels cleanly -->
      <svg width="100%" height="340" viewBox="-240 -160 480 320" class="overflow-visible select-none">
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

        <!-- Fixed Axis Text Labels (14 total elements looping smoothly) -->
        <text
          v-for="(lbl, idx) in radarLabelsArray" :key="'label-'+idx" :x="lbl.x" :y="lbl.y" :text-anchor="lbl.textAnchor" dominant-baseline="central"
          :class="[
            'text-[9px] font-mono transition-all duration-300 font-bold', 
            lbl.isActive ? 'font-black scale-110' : '', 
            getFeatureDirection(featureLabels[idx]).includes('push') ? 'fill-rose-400 font-bold' : 'fill-emerald-400 font-bold'
          ]"
        >
          {{ lbl.name }}
        </text>
      </svg>
    
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
