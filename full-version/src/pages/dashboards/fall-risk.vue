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
  tug_seconds: 12.0
})

const predictionResult = ref(null)
const limeExplanations = ref([])

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
	//suggestions.value = response.data.suggestion
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Prediction request failed.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="p-6 space-y-6">
    <h2 class="text-xl font-bold">Clinical Fall Risk Assessment & LIME Diagnostics</h2>
    
    <!-- Input Form Grid -->
    <div class="grid grid-cols-2 gap-4 bg-white p-6 rounded shadow">
	  <div>
        <label class="block text-sm font-medium">Sex ("M" or "F")</label>
        <input v-model.number="patientData.sex" type="text" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Age (60-100)</label>
        <input v-model.number="patientData.age" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Past Falls (0-5)</label>
        <input v-model.number="patientData.past_falls" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Mobility Score (1-10)</label>
        <input v-model.number="patientData.mobility_score" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">TUG Seconds (8.0-31.9)</label>
        <input v-model.number="patientData.tug_seconds" type="number" step="0.1" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Night Bed Exits (0-8)</label>
        <input v-model.number="patientData.night_bed_exits" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Night Activity Duration (min)</label>
        <input v-model.number="patientData.night_activity_duration_min" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Polypharmacy Count (0-14)</label>
        <input v-model.number="patientData.polypharmacy_count" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Cognitive Impairment (0-2)</label>
        <input v-model.number="patientData.cognitive_impairment" type="number" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">High Risk Medication (0 or 1)</label>
        <input v-model.number="patientData.high_risk_medication" type="number" min="0" max="1" class="border p-2 w-full rounded" />
      </div>
      <div>
        <label class="block text-sm font-medium">Orthostatic Hypotension (0 or 1)</label>
        <input v-model.number="patientData.orthostatic_hypotension" type="number" min="0" max="1" class="border p-2 w-full rounded" />
      </div>

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
      
    </div>
  </div>
</template>
