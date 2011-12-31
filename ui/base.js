"use strict";

/*
A very minimal "unframework" to capture just a few important patterns, make a
few things nicer, less verbose.  But this is *not* a band aid for browser
compatibility, nor for the JavaScript language.

Note that couch.js should never depend on anything in here.
*/


function $(id) {
    /*
    Return the element with id="id".

    If `id` is an Element, it is returned unchanged.

    Examples:

    >>> $('browser');
    <div id="browser" class="box">
    >>> var el = $('browser');
    >>> $(el);
    <div id="browser" class="box">

    */
    if (id instanceof Element) {
        return id;
    }
    return document.getElementById(id);
}


function $el(tag, attributes) {
    /*
    Convenience function to create a new DOM element and set its attributes.

    Examples:

    >>> $el('img');
    <img>
    >>> $el('img', {'class': 'thumbnail', 'src': 'foo.png'});
    <img class="thumbnail" src="foo.png">

    */
    var el = document.createElement(tag);
    if (attributes) {
        var key;
        for (key in attributes) {
            var value = attributes[key];
            if (key == 'textContent') {
                el.textContent = value;
            }
            else {
                el.setAttribute(key, value);
            }
        }
    }
    return el;
}


function $replace(incumbent, replacement) {
    /*
    Replace `incumbent` with `replacement`.

    `incumbent` can be an element or id, `replacement` must be an element.

    Returns the element `incumbent`.
    */
    var incumbent = $(incumbent);
    return incumbent.parentNode.replaceChild(replacement, incumbent);
}


function $hide(el) {
    $(el).classList.add('hide');
}


function $show(el) {
    $(el).classList.remove('hide');
}


var Signal = {
    /*
    Relay signals between JavaScript and Gtk.

    For example, to send a signal to Gtk via document.title:

    >>> Signal.send('click');
    >>> Signal.send('changed', 'foo', 'bar');

    Or from the Gtk side, send a signal to JavaScript by using
    WebView.execute_script() to call Signal.recv() like this:

    >>> Signal.recv('{"signal": "error", "args": ["oops!"]}');

    Use userwebkit.BaseApp.send() as a shortcut to do the above.

    Lastly, to emit a signal from JavaScript to JavaScript handlers, use
    Signal.emit() like this:

    >>> Signal.emit('changed', 'foo', 'bar');

    */
    i: 0,

    names: {},

    connect: function(signal, callback, self) {
        if (! Signal.names[signal]) {
            Signal.names[signal] = [];
        }
        Signal.names[signal].push({callback: callback, self: self});
    },

    send: function() {
        var params = Array.prototype.slice.call(arguments);
        var obj = {
            i: Signal.i,
            signal: params[0],
            args: params.slice(1),
        };
        Signal.i += 1;
        document.title = JSON.stringify(obj);
    },

    recv: function(string) {
        var obj = JSON.parse(string);
        Signal._emit(obj.signal, obj.args);
    },

    emit: function() {
        var params = Array.prototype.slice.call(arguments);
        Signal._emit(params[0], params.slice(1));
    },

    _emit: function(signal, args) {
        /*
        Low-level private function to emit a signal to JavaScript handlers.
        */
        var handlers = Signal.names[signal];
        if (handlers) {
            handlers.forEach(function(h) {
                h.callback.apply(h.self, args);
            });
        }
    },
}

