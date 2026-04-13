<template>
  <div class="diagnosis-page">
    <el-row :gutter="20">
      <!-- 左侧：患者信息录入（诊断开始后隐藏） -->
      <el-col :span="8" v-if="!currentTaskId">
        <el-card class="input-card">
          <template #header>
            <div class="card-header"><span>患者信息录入</span></div>
          </template>

          <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
            <!-- 已有患者选择 -->
            <el-form-item label="已有患者">
              <el-select v-model="selectedUserId" placeholder="新患者（自动建档）" clearable filterable style="width:100%" @change="onSelectUser">
                <el-option v-for="u in userList" :key="u.user_id" :label="`${u.name}（${u.gender}，${u.age}岁）`" :value="u.user_id" />
              </el-select>
            </el-form-item>

            <el-divider />

            <el-form-item label="姓名" prop="name">
              <el-input v-model="form.name" placeholder="请输入患者姓名" :disabled="!!selectedUserId" />
            </el-form-item>

            <el-form-item label="年龄" prop="age">
              <el-input-number v-model="form.age" :min="1" :max="150" :disabled="!!selectedUserId" />
            </el-form-item>

            <el-form-item label="性别" prop="gender">
              <el-radio-group v-model="form.gender" :disabled="!!selectedUserId">
                <el-radio value="男">男</el-radio>
                <el-radio value="女">女</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="既往病史">
              <el-input v-model="form.medical_history" type="textarea" :rows="3" placeholder="如有既往病史请在此说明" />
            </el-form-item>

            <el-form-item label="症状描述" prop="symptoms">
              <el-input v-model="form.symptoms" type="textarea" :rows="6" placeholder="请详细描述症状，如：发热、咳嗽、头痛等" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="startDiagnosis" :loading="loading" style="width: 100%">
                开始诊断
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧（或全宽）：流程可视化 -->
      <el-col :span="currentTaskId ? 24 : 16">
        <el-card class="graph-card">
          <template #header>
            <div class="card-header">
              <span>诊断流程可视化</span>
              <div v-if="currentTaskId" style="display:flex;align-items:center;gap:8px;margin-left:auto">
                <el-tag type="primary">{{ patientName }}</el-tag>
                <el-tag>{{ patientGender }}</el-tag>
                <el-tag>{{ patientAge }}岁</el-tag>
                <el-tag type="info">{{ confirmedUserId }}</el-tag>
                <el-tag type="warning">任务 {{ currentTaskId.substring(0, 8) }}...</el-tag>
                <el-button text type="info" size="small" @click="startNewDiagnosis">新诊断</el-button>
              </div>
            </div>
          </template>

          <div class="graph-container">
            <div v-if="!currentTaskId" class="empty-state">
              <el-empty description="请先输入患者信息并启动诊断流程" />
            </div>

            <div v-else>
              <!-- 进度条 -->
              <el-progress :percentage="progress" :status="progressStatus" :stroke-width="20" style="margin-bottom: 20px" />

              <!-- 当前节点 -->
              <el-alert :title="`当前节点: ${currentNode}`" :type="alertType" :closable="false" show-icon style="margin-bottom: 20px" />

              <el-row :gutter="20">
                <!-- 节点结果 -->
                <el-col :span="16">
                  <div v-if="nodeResults.length > 0" class="node-results">
                    <!-- 历史记录 -->
                    <el-card v-if="nodeResults.find(r => r.node === 'fetch_medical_records')" class="result-card" shadow="hover">
                      <template #header><div class="result-header"><el-icon color="#67c23a"><CircleCheck /></el-icon><span>获取历史记录 (MCP)</span></div></template>
                      <div v-if="medicalRecords.length > 0">
                        <p>找到 <strong>{{ medicalRecords.length }}</strong> 条历史就诊记录</p>
                        <el-collapse><el-collapse-item v-for="(record, index) in medicalRecords" :key="index" :title="`${record.date} - ${record.diagnosis}`"><p><strong>治疗：</strong>{{ record.treatment }}</p><p><strong>医生：</strong>{{ record.doctor }} | {{ record.department }}</p></el-collapse-item></el-collapse>
                      </div>
                      <p v-else>未找到历史记录</p>
                    </el-card>

                    <!-- 初步诊断 -->
                    <el-card v-if="preliminaryDiagnosis" class="result-card" shadow="hover">
                      <template #header><div class="result-header"><el-icon color="#67c23a"><CircleCheck /></el-icon><span>初步诊断（ReAct Agent）</span></div></template>
                      <el-descriptions :column="1" border>
                        <el-descriptions-item label="诊断结果">{{ preliminaryDiagnosis.diagnosis }}</el-descriptions-item>
                        <el-descriptions-item label="诊断依据">{{ preliminaryDiagnosis.basis }}</el-descriptions-item>
                        <el-descriptions-item label="建议科室"><el-tag v-for="dept in preliminaryDiagnosis.suggested_departments" :key="dept" style="margin-right:5px">{{ dept }}</el-tag></el-descriptions-item>
                      </el-descriptions>
                    </el-card>

                    <!-- 会诊结果 -->
                    <el-card v-if="consultationResult" class="result-card" shadow="hover">
                      <template #header><div class="result-header"><el-icon color="#67c23a"><CircleCheck /></el-icon><span>跨科室会诊结果 (SubGraph)</span></div></template>
                      <el-descriptions :column="1" border><el-descriptions-item label="参与科室"><el-tag v-for="dept in consultationResult.departments" :key="dept" type="success" style="margin-right:5px">{{ dept }}</el-tag></el-descriptions-item></el-descriptions>
                      <el-divider>各科室意见</el-divider>
                      <el-collapse><el-collapse-item v-for="(opinion, index) in consultationResult.opinions" :key="index" :title="opinion.department"><p>{{ opinion.opinion }}</p></el-collapse-item></el-collapse>
                      <el-divider>会诊共识</el-divider>
                      <p class="consensus-text">{{ consultationResult.consensus }}</p>
                    </el-card>
                  </div>
                </el-col>

                <!-- 医生操作区 -->
                <el-col :span="8" v-if="showActionButtons">
                  <el-card>
                    <template #header><span style="font-weight:bold">医生操作</span></template>

                    <div v-if="currentNode === 'consultation_decision'">
                      <p style="margin-bottom:15px;font-weight:bold">是否需要跨科室会诊？</p>
                      <el-radio-group v-model="consultationChoice" style="margin-bottom:15px"><el-radio :value="true">需要会诊</el-radio><el-radio :value="false">不需要会诊</el-radio></el-radio-group>
                      <br/><el-button type="primary" @click="submitConsultation" :disabled="consultationChoice === null" style="width:100%">确定</el-button>
                    </div>

                    <div v-if="currentNode === 'doctor_review'">
                      <el-card shadow="hover" style="margin-bottom:15px">
                        <template #header><div class="result-header"><el-icon color="#409eff"><Refresh /></el-icon><span>Time Travel 回溯</span></div></template>
                        <el-button type="warning" @click="rewindToNode('consultation_decision')" :loading="rewinding" style="width:100%"><el-icon><Back /></el-icon> 回溯到会诊决策</el-button>
                      </el-card>
                      <el-form :model="reviewForm" label-width="100px">
                        <el-form-item label="最终诊断"><el-input v-model="reviewForm.modified_diagnosis" type="textarea" :rows="3" placeholder="可修改 AI 诊断结果" /></el-form-item>
                        <el-form-item label="治疗方案"><el-input v-model="reviewForm.modified_treatment" type="textarea" :rows="4" placeholder="可修改 AI 治疗方案" /></el-form-item>
                        <el-form-item label="医生备注"><el-input v-model="reviewForm.doctor_notes" type="textarea" :rows="2" placeholder="额外说明（选填）" /></el-form-item>
                        <el-form-item><el-button type="success" @click="submitReview" :loading="submitting" style="width:100%"><el-icon><Check /></el-icon> 提交诊断报告</el-button></el-form-item>
                      </el-form>
                    </div>

                    <div v-if="status === 'completed'">
                      <el-button type="success" @click="viewReport" style="width:100%;margin-bottom:10px">查看诊断报告</el-button>
                      <el-button @click="viewTimeline" style="width:100%;margin-bottom:10px">查看流程时间线</el-button>
                      <el-button @click="startNewDiagnosis" style="width:100%">发起新诊断</el-button>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Back, Check, Refresh } from '@element-plus/icons-vue'
import { diagnosisAPI } from '../stores/diagnosis'

const router = useRouter()

const userList = ref([])
const selectedUserId = ref('')

const form = ref({ name: '', symptoms: '', age: null, gender: '', medical_history: '' })
const formRef = ref(null)
const formRules = {
  name: [{ required: true, message: '请输入患者姓名', trigger: 'blur' }],
  age: [{ required: true, message: '请输入年龄', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  symptoms: [{ required: true, message: '请描述症状', trigger: 'blur' }]
}

const loadUsers = async () => { try { userList.value = await diagnosisAPI.getUsers() } catch (e) { console.error(e) } }
const onSelectUser = (userId) => {
  if (!userId) { form.value = { ...form.value, name: '', age: null, gender: '', medical_history: '' }; return }
  const u = userList.value.find(x => x.user_id === userId)
  if (u) { form.value.name = u.name; form.value.age = u.age; form.value.gender = u.gender; form.value.medical_history = u.medical_history || '' }
}

const loading = ref(false)
const currentTaskId = ref('')
const confirmedUserId = ref('')
const patientName = ref('')
const patientGender = ref('')
const patientAge = ref(0)
const status = ref('')
const currentNode = ref('')
const progress = ref(0)
const pollingTimer = ref(null)
const rewinding = ref(false)
const submitting = ref(false)

const nodeResults = ref([])
const medicalRecords = ref([])
const preliminaryDiagnosis = ref(null)
const consultationResult = ref(null)

const progressStatus = computed(() => { if (status.value === 'completed') return 'success'; if (status.value === 'failed') return 'exception'; return undefined })
const alertType = computed(() => { if (status.value === 'completed') return 'success'; if (status.value === 'failed') return 'error'; return 'info' })
const showActionButtons = computed(() => ['consultation_decision','doctor_review','completed'].includes(status.value) || ['consultation_decision','doctor_review'].includes(currentNode.value))

const reviewForm = ref({ modified_diagnosis: '', modified_treatment: '', doctor_notes: '' })
const consultationChoice = ref(null)

const startDiagnosis = async () => {
  try { await formRef.value.validate() } catch { ElMessage.warning('请完整填写必填信息'); return }
  loading.value = true
  try {
    const payload = { name: form.value.name, symptoms: form.value.symptoms, age: form.value.age, gender: form.value.gender, medical_history: form.value.medical_history || null }
    if (selectedUserId.value) payload.user_id = selectedUserId.value
    const result = await diagnosisAPI.startDiagnosis(payload)
    currentTaskId.value = result.task_id
    confirmedUserId.value = result.user_id || ''
    patientName.value = form.value.name
    patientGender.value = form.value.gender
    patientAge.value = form.value.age
    ElMessage.success('诊断流程已启动')
    startPolling()
  } catch (error) { ElMessage.error('启动失败: ' + (error.response?.data?.detail || error.message)) } finally { loading.value = false }
}

const startPolling = () => {
  pollingTimer.value = setInterval(async () => {
    try {
      const ts = await diagnosisAPI.getStatus(currentTaskId.value)
      status.value = ts.status; currentNode.value = ts.current_node; progress.value = ts.progress
      nodeResults.value = ts.timeline || []
      if (ts.medical_records && ts.medical_records.length > 0) medicalRecords.value = ts.medical_records
      if (ts.preliminary_diagnosis) preliminaryDiagnosis.value = ts.preliminary_diagnosis
      if (ts.consultation_result) consultationResult.value = ts.consultation_result
      for (const e of (ts.timeline||[])) {
        if (e.node==='fetch_medical_records' && e.data && medicalRecords.value.length===0) medicalRecords.value = e.data.records||[]
        if (e.node==='preliminary_diagnosis' && e.data && !preliminaryDiagnosis.value) preliminaryDiagnosis.value = e.data.diagnosis
        if (e.node==='cross_department_consultation' && e.data && !consultationResult.value) consultationResult.value = e.data.result
      }
      if (['completed','failed'].includes(ts.status)) stopPolling()
    } catch (err) { console.error(err) }
  }, 2000)
}
const stopPolling = () => { if (pollingTimer.value) { clearInterval(pollingTimer.value); pollingTimer.value = null } }

const submitConsultation = async () => {
  if (consultationChoice.value === null) { ElMessage.warning('请选择是否需要会诊'); return }
  try { await diagnosisAPI.confirmConsultation({ task_id: currentTaskId.value, need_consultation: consultationChoice.value, departments: consultationChoice.value ? ['内科','外科'] : [] }); ElMessage.success('会诊确认已提交'); consultationChoice.value = null; stopPolling(); startPolling() } catch (error) { ElMessage.error('确认失败: ' + error.message) }
}
const submitReview = async () => {
  if (!reviewForm.value.modified_diagnosis || !reviewForm.value.modified_treatment) { ElMessage.warning('请填写诊断和治疗方案'); return }
  submitting.value = true
  try { await diagnosisAPI.modifyDiagnosis({ task_id: currentTaskId.value, modified_diagnosis: reviewForm.value.modified_diagnosis, modified_treatment: reviewForm.value.modified_treatment, doctor_notes: reviewForm.value.doctor_notes }); ElMessage.success('已提交，正在生成报告...'); stopPolling(); startPolling() } catch (error) { ElMessage.error('提交失败: ' + error.message) } finally { submitting.value = false }
}
const viewReport = () => router.push(`/report/${currentTaskId.value}`)
const viewTimeline = () => router.push(`/timeline/${currentTaskId.value}`)
const rewindToNode = async (targetNode) => {
  try {
    await ElMessageBox.confirm('确定要回溯到会诊决策节点吗？系统将清空后续结果。','Time Travel 确认',{confirmButtonText:'确定回溯',cancelButtonText:'取消',type:'warning'})
    rewinding.value = true
    const response = await fetch(`/api/rewind/${currentTaskId.value}?target_node=${targetNode}`,{method:'POST'})
    if (!response.ok) throw new Error('回溯失败')
    const result = await response.json()
    ElMessage.success('已回溯到会诊决策'); status.value = result.status; currentNode.value = result.current_node; consultationResult.value = null; stopPolling(); startPolling()
  } catch (error) { if (error !== 'cancel') ElMessage.error('回溯失败: ' + (error.message||'')) } finally { rewinding.value = false }
}
const startNewDiagnosis = () => {
  currentTaskId.value = ''; confirmedUserId.value = ''; selectedUserId.value = ''
  status.value = ''; currentNode.value = ''; progress.value = 0; nodeResults.value = []; medicalRecords.value = []
  preliminaryDiagnosis.value = null; consultationResult.value = null
  reviewForm.value = { modified_diagnosis: '', modified_treatment: '', doctor_notes: '' }
  form.value = { name: '', symptoms: '', age: null, gender: '', medical_history: '' }
  stopPolling(); loadUsers()
}
onMounted(() => { loadUsers() })
onUnmounted(() => { stopPolling() })
</script>

<style scoped>
.diagnosis-page { max-width: 1400px; margin: 0 auto; }
.card-header { display: flex; align-items: center; justify-content: space-between; font-weight: bold; }
.graph-container { min-height: 600px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 500px; }
.result-card { margin-bottom: 15px; }
.result-header { display: flex; align-items: center; gap: 8px; font-weight: bold; }
.consensus-text { line-height: 1.8; color: #606266; background: #f5f7fa; padding: 15px; border-radius: 4px; }
.node-results { margin-bottom: 20px; }
</style>