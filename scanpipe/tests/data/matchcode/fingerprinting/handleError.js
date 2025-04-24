'use strict';

var gutil = require('gulp-util');

function handleError(error, source) {
	var message = error.messageFormatted ? error.messageFormatted : error.message;
	console.error(new gutil.PluginError(source || 'metal', message).toString());

	this.emit('end'); // jshint ignore:line
}

module.exports = handleError;
