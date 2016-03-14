var Stats = function(options) {
    this.initialize(options);
};

Stats.prototype = {
    constructor: Stats,

    defaults: {
        deflocation: "graphs/",
        language: "en"
    },

    initialize: function(options) {
        this.options = $.extend({}, this.defaults, options);
        this.options.defcallback = $.proxy(this.graphs_cb, this);

        var navobj = new History(this.options);
        this.navobj = navobj;

        if (navobj.params.searchquery != undefined) {
            $("#searchquery").val(navobj.params.searchquery);
        }
        $("#searchquery").focus(function() {
            var $this = $(this);
            if ($this.val() == undefined) {
                return;
            }
            $this.data("oldvalue", $this.val());
            $this.val("");
        }).blur(function() {
            var $this = $(this);
            if ($this.val() == "") {
                if ($this.data("oldvalue")) {
                    $this.val($this.data('oldvalue'));
                    $this.data("oldvalue", null);
                } else {
                    $this.val(gettext("Search a domain"));
                }
            }
        });
        if (navobj.params.start) {
            $("#id_from").val(navobj.params.start);
        }
        if (navobj.params.end) {
            $("#id_to").val(navobj.params.end);
        }
        $("#custom-period input").datepicker({
            format: 'yyyy-mm-dd',
            autoclose: true,
            todayHighlight: true,
            language: this.options.language
        });
        $("#searchquery").autocompleter({
            choices: get_domains_list,
            choice_selected: $.proxy(this.search_domain, this),
            empty_choice: $.proxy(this.reset_search, this)
        });

        this.register_nav_callbacks();
        this.listen();
    },

    listen: function() {
        $(".period_selector").click($.proxy(this.change_period, this));
        $("#customsend").on("click", $.proxy(this.customgraphs, this));
    },

    register_nav_callbacks: function() {
        this.navobj.register_callback("graphs",
            $.proxy(this.graphs_cb, this));
    },

    change_period: function(e) {
        e.preventDefault();
        var $link = $(e.target);

        this.navobj.delparam("start").delparam("end");
        this.navobj.setparam("period", $link.attr("data-period")).update();
    },

    graphs_cb: function(data) {
        if (data.status == "ko") {
            $("body").notify("error", data.respmsg);
            return;
        }
        if (data.content) {
            $(".tab-pane.active").html(data.content);
        }
    },

    search_domain: function(value) {
        this.navobj.setparam("searchquery", value).update();
    },

    reset_search: function() {
        $("#searchquery").data("oldvalue", null);
        this.navobj.delparam("searchquery").update();
    },

    customgraphs: function(e) {
        e.preventDefault();
        var $fromdate = $("#id_from");
        var $todate = $("#id_to");

        if ($fromdate.val() == "" || $todate.val() == "") {
            return;
        }
        this.navobj.setparams({
            period: "custom",
            start: $fromdate.val(),
            end: $todate.val()
        }).update();
    }
};
