import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120000,  // 增加到120秒，适应LLM生成时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    console.log('API Request:', config.method.toUpperCase(), config.url)
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error.message)
    return Promise.reject(error)
  }
)

export default apiClient
