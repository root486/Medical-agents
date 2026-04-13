import api from '../utils/api'

export const diagnosisAPI = {
  startDiagnosis(data) {
    return api.post('/start-diagnosis', data)
  },
  getStatus(taskId) {
    return api.get(`/status/${taskId}`)
  },
  confirmConsultation(data) {
    return api.post('/consult/confirm', data)
  },
  modifyDiagnosis(data) {
    return api.post('/review/modify', data)
  },
  getReport(taskId) {
    return api.get(`/report/${taskId}`)
  },
  getTimeline(taskId) {
    return api.get(`/timeline/${taskId}`)
  },
  getGraphStructure() {
    return api.get('/graph/structure')
  },
  getUsers() {
    return api.get('/users')
  }
}
