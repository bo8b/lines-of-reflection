// lines.js

Module.register("lines",{
  defaults: {filename: '/home/pi/MagicMirror/modules/lines/output.txt', updateInterval: 1, font: 'medium'},

  start() {
    Log.info(`Starting module: ${this.name}`);
    this.content = '';
    this.readFile();
    setInterval(() => {
      this.readFile();
    }, this.config.updateInterval * 1000); // update every <updateInterval> seconds
  },

  readFile() {
    this.sendSocketNotification('READ_FILE_CONTENTS', this.config.filename);
  },

  getDom() {
    const wrapper = document.createElement('div');
    wrapper.classList.add(this.config.font);
    wrapper.style.textAlign = 'left';

    const preformatted = document.createElement('pre');
    preformatted.innerHTML = this.content;

    wrapper.appendChild(preformatted);
    return wrapper;
  },

  socketNotificationReceived(notification, payload) {
    if (notification === 'TEXT_FILE_CONTENTS') {
      this.content = payload.content;
      this.updateDom();
    }
  }
});
