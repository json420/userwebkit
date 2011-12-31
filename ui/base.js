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


var Hub = {
    /*
    Relay signals between JavaScript and Gtk.

    For example, to send a signal to Gtk via document.title:

    >>> Hub.send('click');
    >>> Hub.send('changed', 'foo', 'bar');

    Or from the Gtk side, send a signal to JavaScript by using
    WebView.execute_script() to call Hub.recv() like this:

    >>> Hub.recv('{"signal": "error", "args": ["oops!"]}');

    Use userwebkit.BaseApp.send() as a shortcut to do the above.

    Lastly, to emit a signal from JavaScript to JavaScript handlers, use
    Hub.emit() like this:

    >>> Hub.emit('changed', 'foo', 'bar');

    */
    i: 0,

    names: {},

    connect: function(signal, callback, self) {
        /*
        Connect a signal handler.

        For example:

        >>> Hub.connect('changed', this.on_changed, this);

        */
        if (! Hub.names[signal]) {
            Hub.names[signal] = [];
        }
        Hub.names[signal].push({callback: callback, self: self});
    },

    send: function() {
        /*
        Send a signal to the Gtk side by changing document.title.

        For example:

        >>> Hub.send('changed', 'foo', 'bar');

        */
        var params = Array.prototype.slice.call(arguments);
        var signal = params[0];
        var args = params.slice(1);
        Hub._emit(signal, args);
        var obj = {
            'i': Hub.i,
            'signal': signal,
            'args': args,
        };
        Hub.i += 1;
        document.title = JSON.stringify(obj);
    },

    recv: function(data) {
        /*
        Gtk should call this function to emit a signal to JavaScript handlers.
        
        For example:

        >>> Hub.recv('{"signal": "changed", "args": ["foo", "bar"]}');

        If you need to emit a signal from JavaScript to JavaScript handlers,
        use Hub.emit() instead.
        */
        var obj = JSON.parse(data);
        Hub._emit(obj.signal, obj.args);
    },

    emit: function() {
        /*
        Emit a signal from JavaScript to JavaScript handlers.

        For example:

        >>> Hub.emit('changed', 'foo', 'bar');

        */
        var params = Array.prototype.slice.call(arguments);
        Hub._emit(params[0], params.slice(1));
    },

    _emit: function(signal, args) {
        /*
        Low-level private function to emit a signal to JavaScript handlers.
        */
        var handlers = Hub.names[signal];
        if (handlers) {
            handlers.forEach(function(h) {
                h.callback.apply(h.self, args);
            });
        }
    },
}

