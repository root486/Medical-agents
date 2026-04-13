<template>
  <div class="timeline-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>流程回溯 (Time Travel)</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>
      
      <div v-loading="loading">
        <el-descriptions title="任务信息" :column="2" border>
          <el-descriptions-item label="任务ID">{{ taskId }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="getStatusType(timelineData.current_status)">
              {{ timelineData.current_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前节点" :span="2">
            {{ timelineData.current_node }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <h3>执行时间线</h3>
        
        <el-timeline>
          <el-timeline-item
            v-for="(event, index) in timelineData.timeline"
            :key="index"
            :timestamp="formatTime(event.timestamp)"
            placement="top"
            :type="getEventType(event.status)"
          >
            <el-card>
              <h4>{{ getNodeLabel(event.node) }}</h4>
              <p>{{ event.message }}</p>
              <el-tag size="small" :type="getEventTagType(event.status)">
                {{ event.status }}
              </el-tag>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        
        <el-divider />
        
        <div class="summary">
          <h3>流程统计</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="总节点数" :value="timelineData.timeline.length" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="已完成" :value="completedCount" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="等待人工" :value="waitingCount" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="失败" :value="failedCount" />
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { diagnosisAPI } from '../stores/diagnosis'

const route = useRoute()
const taskId = route.params.taskId

const loading = ref(false)
const timelineData = ref({
  task_id: '',
  timeline: [],
  current_status: '',
  current_node: ''
})

// 节点标签映射
const nodeLabels = {
  '__start__': '开始',
  'task_summary': '诊断任务汇总',
  'fetch_medical_records': '获取用户历史诊断记录',
  'preliminary_diagnosis': '初步诊断',
  'consultation_decision': '会诊决策',
  'cross_department_consultation': '跨科室会诊',
  'doctor_review': '医生复诊',
  'final_summary': '最终汇总',
  'rewind': '回溯操作',
  '__end__': '结束'
}

// 计算属性
const completedCount = computed(() => {
  return timelineData.value.timeline.filter(e => e.status === 'completed').length
})

const waitingCount = computed(() => {
  return timelineData.value.timeline.filter(e => e.status === 'waiting_human').length
})

const failedCount = computed(() => {
  return timelineData.value.timeline.filter(e => e.status === 'failed').length
})

// 获取时间线
const fetchTimeline = async () => {
  loading.value = true
  try {
    timelineData.value = await diagnosisAPI.getTimeline(taskId)
  } catch (error) {
    ElMessage.error('获取时间线失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

// 获取节点标签
const getNodeLabel = (nodeId) => {
  return nodeLabels[nodeId] || nodeId
}

// 获取事件类型
const getEventType = (status) => {
  const typeMap = {
    'completed': 'success',
    'waiting_human': 'warning',
    'failed': 'danger',
    'pending': 'info'
  }
  return typeMap[status] || 'primary'
}

// 获取事件标签类型
const getEventTagType = (status) => {
  return getEventType(status)
}

// 获取状态类型
const getStatusType = (status) => {
  const typeMap = {
    'completed': 'success',
    'failed': 'danger',
    'pending': 'info',
    'waiting_human': 'warning'
  }
  return typeMap[status] || ''
}

onMounted(() => {
  fetchTimeline()
})
</script>

<style scoped>
.timeline-page {
  max-width: 1000px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h3 {
  margin-top: 20px;
  margin-bottom: 15px;
  color: #303133;
}

h4 {
  margin: 0 0 10px 0;
  color: #409eff;
}

.summary {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}
</style>
