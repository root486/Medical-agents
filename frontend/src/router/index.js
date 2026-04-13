import { createRouter, createWebHistory } from 'vue-router'
import DiagnosisPage from '../views/DiagnosisPage.vue'
import ReportPage from '../views/ReportPage.vue'
import TimelinePage from '../views/TimelinePage.vue'

const routes = [
  {
    path: '/',
    name: 'Diagnosis',
    component: DiagnosisPage
  },
  {
    path: '/report/:taskId',
    name: 'Report',
    component: ReportPage,
    props: true
  },
  {
    path: '/timeline/:taskId',
    name: 'Timeline',
    component: TimelinePage,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
