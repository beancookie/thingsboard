(function () {
  var base = (document.body.dataset.base || "").replace(/\/$/, "");

  function byId(id) {
    return document.getElementById(id);
  }

  function openDialog(id) {
    var dialog = byId(id);
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }

  function closeDialog(id) {
    var dialog = byId(id);
    if (dialog && dialog.open) {
      dialog.close();
    }
  }

  function copyText(text, button) {
    var done = function () {
      var icon = button.querySelector(".material-icons");
      if (icon) {
        var original = icon.textContent;
        icon.textContent = "check";
        setTimeout(function () {
          icon.textContent = original;
        }, 1200);
      }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {});
    } else {
      var input = document.createElement("textarea");
      input.value = text;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      done();
    }
  }

  function openEdit(row) {
    var id = row.dataset.id;
    fetch(base + "/api/cameras/" + id)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("failed to load camera");
        }
        return response.json();
      })
      .then(function (camera) {
        byId("edit-form").action = base + "/cameras/" + id;
        byId("edit-path").value = camera.path || "";
        byId("edit-name").value = camera.display_name || "";
        byId("edit-location").value = camera.location || "";
        byId("edit-description").value = camera.description || "";
        byId("edit-enabled").checked = !!camera.enabled;
        byId("edit-push-username").value = camera.push_username || "";
        byId("edit-push-password").value = camera.push_password || "";
        openDialog("edit-drawer");
      })
      .catch(function () {
        window.alert("加载摄像头信息失败");
      });
  }

  function openDelete(row) {
    var data = row.dataset;
    byId("delete-form").action = base + "/cameras/" + data.id + "/delete";
    byId("delete-name").textContent = data.name || data.path || "";
    openDialog("confirm-dialog");
  }

  var previewRow = null;

  function applyPreviewProtocol(protocol) {
    if (!previewRow) {
      return;
    }
    var url = protocol === "webrtc" ? previewRow.dataset.webrtcUrl : previewRow.dataset.hlsUrl;
    byId("preview-iframe").src = url || "";
    byId("preview-address").value = url || "";
    Array.prototype.forEach.call(document.querySelectorAll(".tb-protocol-btn"), function (button) {
      button.classList.toggle("active", button.getAttribute("data-protocol") === protocol);
    });
  }

  function openPreview(row) {
    previewRow = row;
    byId("preview-title").textContent = row.dataset.name || row.dataset.path || "画面预览";
    applyPreviewProtocol("hls");
    openDialog("preview-dialog");
  }

  var tbody = byId("camera-tbody");
  if (tbody) {
    var table = byId("media-table");
    var emptyRow = byId("camera-empty-row");
    var allRows = Array.prototype.slice.call(tbody.querySelectorAll("tr.tb-product-row"));
    var pageSize = 50;
    var page = 0;
    var totalPages = 1;
    var query = "";
    var sortKey = "";
    var sortDir = 1;

    function rowValue(row, key) {
      if (key === "enabled") {
        return row.dataset.enabled === "true" ? 1 : 0;
      }
      return (row.dataset[key] || "").toLowerCase();
    }

    function renderTable() {
      var filtered = allRows.filter(function (row) {
        return !query || row.textContent.toLowerCase().indexOf(query) !== -1;
      });

      if (sortKey) {
        filtered.sort(function (a, b) {
          var av = rowValue(a, sortKey);
          var bv = rowValue(b, sortKey);
          if (typeof av === "number") {
            return (av - bv) * sortDir;
          }
          return av.localeCompare(bv) * sortDir;
        });
        filtered.forEach(function (row) {
          tbody.insertBefore(row, emptyRow);
        });
      }

      var total = filtered.length;
      totalPages = Math.max(1, Math.ceil(total / pageSize));
      if (page > totalPages - 1) {
        page = totalPages - 1;
      }
      if (page < 0) {
        page = 0;
      }
      var start = page * pageSize;
      var end = Math.min(start + pageSize, total);

      allRows.forEach(function (row) {
        row.style.display = "none";
      });
      filtered.slice(start, end).forEach(function (row) {
        row.style.display = "";
      });
      emptyRow.style.display = total === 0 ? "" : "none";

      byId("page-range").textContent = (start + 1) + " – " + end + "  / " + total;
      byId("page-first").disabled = page === 0;
      byId("page-prev").disabled = page === 0;
      byId("page-next").disabled = page >= totalPages - 1;
      byId("page-last").disabled = page >= totalPages - 1;
    }

    Array.prototype.forEach.call(table.querySelectorAll("th[data-sort]"), function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort");
        if (sortKey === key) {
          sortDir = -sortDir;
        } else {
          sortKey = key;
          sortDir = 1;
        }
        Array.prototype.forEach.call(table.querySelectorAll("th[data-sort]"), function (other) {
          other.classList.remove("sort-asc", "sort-desc");
          var icon = other.querySelector(".tb-sort-icon");
          if (icon) {
            icon.textContent = "arrow_upward";
          }
        });
        th.classList.add(sortDir === 1 ? "sort-asc" : "sort-desc");
        var icon = th.querySelector(".tb-sort-icon");
        if (icon) {
          icon.textContent = sortDir === 1 ? "arrow_upward" : "arrow_downward";
        }
        renderTable();
      });
    });

    var normalToolbar = byId("toolbar-normal");
    var searchToolbar = byId("toolbar-search");
    var searchInput = byId("search-input");

    byId("search-btn").addEventListener("click", function () {
      normalToolbar.classList.add("hidden");
      searchToolbar.classList.remove("hidden");
      searchInput.focus();
    });

    byId("search-close-btn").addEventListener("click", function () {
      searchToolbar.classList.add("hidden");
      normalToolbar.classList.remove("hidden");
      searchInput.value = "";
      query = "";
      page = 0;
      renderTable();
    });

    searchInput.addEventListener("input", function () {
      query = searchInput.value.trim().toLowerCase();
      page = 0;
      renderTable();
    });

    byId("page-size").addEventListener("change", function () {
      pageSize = parseInt(this.value, 10) || 50;
      page = 0;
      renderTable();
    });

    byId("page-first").addEventListener("click", function () {
      page = 0;
      renderTable();
    });

    byId("page-prev").addEventListener("click", function () {
      if (page > 0) {
        page -= 1;
        renderTable();
      }
    });

    byId("page-next").addEventListener("click", function () {
      if (page < totalPages - 1) {
        page += 1;
        renderTable();
      }
    });

    byId("page-last").addEventListener("click", function () {
      page = totalPages - 1;
      renderTable();
    });

    tbody.addEventListener("click", function (event) {
      if (event.target.closest("button, input, select, a, textarea")) {
        return;
      }
      var row = event.target.closest("tr.tb-product-row");
      if (row) {
        openEdit(row);
      }
    });

    renderTable();
  }

  document.addEventListener("click", function (event) {
    var actionButton = event.target.closest("[data-action]");
    if (actionButton) {
      var row = actionButton.closest("tr[data-id]");
      if (row) {
        var action = actionButton.getAttribute("data-action");
        if (action === "delete") {
          openDelete(row);
        } else if (action === "preview") {
          openPreview(row);
        }
      }
      return;
    }

    var closeButton = event.target.closest("[data-close]");
    if (closeButton) {
      closeDialog(closeButton.getAttribute("data-close"));
      return;
    }

    var copyButton = event.target.closest("[data-copy]");
    if (copyButton) {
      copyText(copyButton.getAttribute("data-copy"), copyButton);
    }
  });

  var addButton = byId("add-camera-btn");
  if (addButton) {
    addButton.addEventListener("click", function () {
      byId("add-form").reset();
      openDialog("add-dialog");
    });
  }

  var refreshButton = byId("refresh-btn");
  if (refreshButton) {
    refreshButton.addEventListener("click", function () {
      window.location.reload();
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll(".tb-protocol-btn"), function (button) {
    button.addEventListener("click", function () {
      applyPreviewProtocol(button.getAttribute("data-protocol"));
    });
  });

  var previewCopy = byId("preview-copy");
  if (previewCopy) {
    previewCopy.addEventListener("click", function () {
      copyText(byId("preview-address").value, previewCopy);
    });
  }

  var previewDialog = byId("preview-dialog");
  if (previewDialog) {
    previewDialog.addEventListener("close", function () {
      byId("preview-iframe").src = "about:blank";
      previewRow = null;
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("dialog"), function (dialog) {
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        dialog.close();
      }
    });
  });

  if (window.__tbOpenDialog) {
    openDialog(window.__tbOpenDialog);
  }
})();
