<template>
  <div class="report-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>诊断报告</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>
      
      <div v-loading="loading">
        <el-descriptions title="基本信息" :column="2" border>
          <el-descriptions-item label="任务ID">{{ report.task_id }}</el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ report.user_id }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatTime(report.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="report.status === 'completed' ? 'success' : 'info'">
              {{ report.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <el-descriptions title="症状信息" :column="1" border>
          <el-descriptions-item label="症状描述">{{ report.symptoms }}</el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <div v-if="report.medical_records && report.medical_records.length > 0">
          <h3>历史医疗记录</h3>
          <el-table :data="report.medical_records" border style="margin-top: 10px">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="department" label="科室" width="120" />
            <el-table-column prop="diagnosis" label="诊断" />
            <el-table-column prop="treatment" label="治疗" />
            <el-table-column prop="doctor" label="医生" width="100" />
          </el-table>
        </div>
        
        <el-divider />
        
        <div v-if="report.preliminary_diagnosis">
          <h3>初步诊断</h3>
          <el-card shadow="never" style="margin-top: 10px">
            <p><strong>诊断结果：</strong>{{ report.preliminary_diagnosis.diagnosis }}</p>
            <p><strong>诊断依据：</strong>{{ report.preliminary_diagnosis.basis }}</p>
            <p v-if="report.preliminary_diagnosis.suggested_departments">
              <strong>建议科室：</strong>
              <el-tag 
                v-for="dept in report.preliminary_diagnosis.suggested_departments" 
                :key="dept"
                style="margin-left: 5px"
              >
                {{ dept }}
              </el-tag>
            </p>
          </el-card>
        </div>
        
        <el-divider />
        
        <div v-if="report.consultation_result">
          <h3>会诊结果</h3>
          <el-card shadow="never" style="margin-top: 10px">
            <p><strong>参与科室：</strong></p>
            <el-tag 
              v-for="dept in report.consultation_result.departments" 
              :key="dept"
              style="margin: 5px"
            >
              {{ dept }}
            </el-tag>
            
            <el-divider />
            
            <div v-for="opinion in report.consultation_result.opinions" :key="opinion.department">
              <p><strong>{{ opinion.department }}：</strong>{{ opinion.opinion }}</p>
            </div>
            
            <el-divider />
            
            <p><strong>会诊共识：</strong></p>
            <el-alert
              :title="report.consultation_result.consensus"
              type="info"
              :closable="false"
            />
          </el-card>
        </div>
        
        <el-divider />
        
        <h3>最终诊断</h3>
        <el-card shadow="never" style="margin-top: 10px; background: #f0f9ff">
          <h4 style="color: #409eff">{{ report.final_diagnosis }}</h4>
        </el-card>
        
        <el-divider />
        
        <h3>治疗方案</h3>
        <el-card shadow="never" style="margin-top: 10px">
          <div style="white-space: pre-wrap">{{ report.treatment_plan }}</div>
        </el-card>
        
        <el-divider />
        
        <div v-if="report.doctor_notes">
          <h3>医生备注</h3>
          <el-card shadow="never" style="margin-top: 10px">
            <div style="white-space: pre-wrap">{{ report.doctor_notes }}</div>
          </el-card>
        </div>
        
        <el-divider />
        
        <div class="action-buttons">
          <el-button type="primary" @click="printReport">打印报告</el-button>
          <el-button @click="$router.push(`/timeline/${taskId}`)">查看流程回溯</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { diagnosisAPI } from '../stores/diagnosis'

const route = useRoute()
const taskId = route.params.taskId

const loading = ref(false)
const report = ref({})

// 获取报告
const fetchReport = async () => {
  loading.value = true
  try {
    report.value = await diagnosisAPI.getReport(taskId)
  } catch (error) {
    ElMessage.error('获取报告失败: ' + error.message)
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

// 打印报告
const printReport = () => {
  window.print()
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
.report-page {
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
  margin-bottom: 10px;
  color: #303133;
}

h4 {
  margin: 0;
}

.action-buttons {
  text-align: center;
  margin-top: 30px;
}

@media print {
  .action-buttons {
    display: none;
  }
}
</style>
