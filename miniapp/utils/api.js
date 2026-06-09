const API = 'https://62.234.145.131'

function request(url, method = 'GET', data = {}) {
  const app = getApp()
  const token = app.globalData.token

  return new Promise((resolve, reject) => {
    wx.request({
      url: API + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json'
      },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // token expired, clear
          wx.removeStorageSync('token')
          app.globalData.token = ''
          app.globalData.user = null
          reject({ code: 401, msg: '登录已过期' })
        } else {
          reject(res.data)
        }
      },
      fail(err) {
        reject({ code: -1, msg: '网络错误' })
      }
    })
  })
}

module.exports = {
  // 注册
  register(email, password) {
    return request('/api/register', 'POST', { email, password })
  },

  // 登录
  login(email, password) {
    return request('/api/login', 'POST', { email, password })
  },

  // 获取用户信息
  getMe(token) {
    return request(`/api/me?token=${token}`)
  },

  // 推荐查询
  recommend(data) {
    const app = getApp()
    let url = `/api/recommend`
    if (app.globalData.token) {
      url += `?token=${app.globalData.token}`
    }
    return request(url, 'POST', {
      score: data.score,
      rank: data.rank,
      province: data.province,
      category: data.category,
      major_category: data.major || null,
      top_n: data.top_n || 20
    })
  },

  // 获取省份列表
  getProvinces() {
    return request('/api/provinces')
  },

  // 获取院校详情
  getSchoolDetail(uid, province, category) {
    return request(`/api/school/${uid}?province=${province}&category=${category}`)
  }
}
