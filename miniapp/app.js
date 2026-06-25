App({
  globalData: {
    API_BASE: 'https://62.234.145.131',
    token: '',
    user: null
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
      this.fetchUser()
    }
  },

  fetchUser() {
    if (!this.globalData.token) return
    wx.request({
      url: `${this.globalData.API_BASE}/api/me?token=${this.globalData.token}`,
      success: (res) => {
        if (res.data && res.data.user) {
          this.globalData.user = res.data.user
        }
      }
    })
  }
})
