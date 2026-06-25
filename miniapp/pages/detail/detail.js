const api = require('../../utils/api')

Page({
  data: {
    loading: true,
    uni: null,
    history: [],
    majors: [],
    province: '',
    category: ''
  },

  onLoad(options) {
    const uid = options.id
    const province = options.province || ''
    const category = options.category || '理科'
    this.setData({ province, category })

    if (!uid) {
      wx.showToast({ title: '参数错误', icon: 'none' })
      return
    }

    api.getSchoolDetail(uid, province, category).then(res => {
      this.setData({
        loading: false,
        uni: res.university,
        history: res.history || [],
        majors: res.majors || []
      })
      // 加载招生政策
      api.getPolicy(uid).then(policyRes => {
        this.setData({ policy: policyRes.policy })
      }).catch(() => {
        this.setData({ policy: null })
      })
    }).catch(err => {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  }
})
