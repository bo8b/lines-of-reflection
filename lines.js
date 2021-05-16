// Like with node_helper.js, some of this code was lifted from Martin Meinke at github.com/martinmeinke/MMM-display-text-file

Module.register("lines",{
  defaults: {filename: '/home/pi/MagicMirror/modules/lines/output.txt', updateInterval: 1, font: 'medium'},


  // Define required scripts.
  getStyles: function () {
    return ["lines.css"];
  },

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
    wrapper.style.width = '800px';
    wrapper.style.textAlign = 'left';
    wrapper.style.wordWrap = 'break-word';

    const preformatted = document.createElement('p');
    preformatted.style.width = '800px';
    preformatted.style.textAlign = 'left';
    preformatted.style.wordWrap = 'break-word';
    preformatted.innerHTML = this.content;

    wrapper.appendChild(preformatted);
    return wrapper;
  },

  socketNotificationReceived(notification, payload) {
    if (notification === 'TEXT_FILE_CONTENTS') {
      this.content = payload.content.split("\n").slice(-6).join("<br>\n");
      this.updateDom();
    }
  }
});
