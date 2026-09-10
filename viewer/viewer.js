/**
 * Interactive Three.js 3D Web Viewer & Pipeline Frontend.
 */

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Embedded fallback sample scene data (Lane 3 schema)
const FALLBACK_SCENE = {
  "format_version": "1.0.0",
  "scene_metadata": {
    "generator": "Lane2-OOP-Model",
    "target_units": "m",
    "element_count": 8,
    "scene_bounds": { "min": [0.0, 0.0, 0.0], "max": [5.2, 4.2, 2.8] }
  },
  "objects": [
    {
      "id": "wall_001",
      "name": "Wall_001",
      "category": "architectural",
      "type": "wall",
      "geometry": { "primitive": "box", "dimensions": { "width": 5.0, "depth": 0.2, "height": 2.8 } },
      "transform": { "translation": { "x": 2.5, "y": 0.1, "z": 1.4 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "WallMaterial", "color": [0.8, 0.8, 0.8, 1.0], "roughness": 0.7, "metallic": 0.0 }
    },
    {
      "id": "wall_002",
      "name": "Wall_002",
      "category": "architectural",
      "type": "wall",
      "geometry": { "primitive": "box", "dimensions": { "width": 0.2, "depth": 4.0, "height": 2.8 } },
      "transform": { "translation": { "x": 5.1, "y": 2.0, "z": 1.4 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "WallMaterial", "color": [0.8, 0.8, 0.8, 1.0], "roughness": 0.7, "metallic": 0.0 }
    },
    {
      "id": "wall_003",
      "name": "Wall_003",
      "category": "architectural",
      "type": "wall",
      "geometry": { "primitive": "box", "dimensions": { "width": 5.0, "depth": 0.2, "height": 2.8 } },
      "transform": { "translation": { "x": 2.5, "y": 4.1, "z": 1.4 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "WallMaterial", "color": [0.8, 0.8, 0.8, 1.0], "roughness": 0.7, "metallic": 0.0 }
    },
    {
      "id": "wall_004",
      "name": "Wall_004",
      "category": "architectural",
      "type": "wall",
      "geometry": { "primitive": "box", "dimensions": { "width": 0.2, "depth": 4.0, "height": 2.8 } },
      "transform": { "translation": { "x": 0.1, "y": 2.0, "z": 1.4 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "WallMaterial", "color": [0.8, 0.8, 0.8, 1.0], "roughness": 0.7, "metallic": 0.0 }
    },
    {
      "id": "door_001",
      "name": "Door_001",
      "category": "architectural",
      "type": "door",
      "geometry": { "primitive": "box", "dimensions": { "width": 0.9, "depth": 0.2, "height": 2.1 } },
      "transform": { "translation": { "x": 2.45, "y": 0.1, "z": 1.05 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "WoodDoorMaterial", "color": [0.55, 0.35, 0.2, 1.0], "roughness": 0.5, "metallic": 0.0 }
    },
    {
      "id": "window_001",
      "name": "Window_001",
      "category": "architectural",
      "type": "window",
      "geometry": { "primitive": "box", "dimensions": { "width": 1.2, "depth": 0.2, "height": 1.2 } },
      "transform": { "translation": { "x": 4.1, "y": 0.1, "z": 1.5 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "GlassMaterial", "color": [0.6, 0.8, 0.9, 0.4], "roughness": 0.1, "metallic": 0.1 }
    },
    {
      "id": "table_001",
      "name": "Table_001",
      "category": "furniture",
      "type": "table",
      "geometry": { "primitive": "box", "dimensions": { "width": 1.4, "depth": 0.8, "height": 0.75 } },
      "transform": { "translation": { "x": 3.2, "y": 2.4, "z": 0.375 }, "rotation": { "x": 0, "y": 0, "z": 0 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "TableMaterial", "color": [0.4, 0.25, 0.15, 1.0], "roughness": 0.6, "metallic": 0.0 }
    },
    {
      "id": "chair_001",
      "name": "Chair_001",
      "category": "furniture",
      "type": "chair",
      "geometry": { "primitive": "box", "dimensions": { "width": 0.5, "depth": 0.5, "height": 0.9 } },
      "transform": { "translation": { "x": 2.75, "y": 2.75, "z": 0.45 }, "rotation": { "x": 0, "y": 0, "z": 180 }, "scale": { "x": 1, "y": 1, "z": 1 } },
      "material": { "name": "FabricChairMaterial", "color": [0.2, 0.3, 0.5, 1.0], "roughness": 0.8, "metallic": 0.0 }
    }
  ]
};

class SceneViewer {
  constructor() {
    this.container = document.getElementById("canvas-container");
    this.interactiveObjects = [];
    this.selectedMesh = null;
    this.wireframeMode = false;
    this.loadedBlueprints = new Map();

    this.initThree();
    this.initLights();
    this.initHelpers();
    this.initEvents();

    // Load initial scene via API or fallback
    this.loadPreset("/api/sample", "Sample Floorplan (8 elements)");
    this.animate();
  }

  initThree() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x12151c);

    const aspect = window.innerWidth / window.innerHeight;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 2000);
    this.camera.position.set(5, -7, 6);
    this.camera.up.set(0, 0, 1); // Z is UP in architectural CAD

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.target.set(2.5, 2.0, 1.0);

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
  }

  initLights() {
    const ambient = new THREE.AmbientLight(0xffffff, 0.65);
    this.scene.add(ambient);

    const sun = new THREE.DirectionalLight(0xffffff, 0.85);
    sun.position.set(15, -20, 25);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    const d = 40;
    sun.shadow.camera.left = -d;
    sun.shadow.camera.right = d;
    sun.shadow.camera.top = d;
    sun.shadow.camera.bottom = -d;
    this.scene.add(sun);
  }

  initHelpers() {
    const grid = new THREE.GridHelper(100, 100, 0x444455, 0x222233);
    grid.rotation.x = Math.PI / 2;
    this.scene.add(grid);

    const axes = new THREE.AxesHelper(3);
    this.scene.add(axes);
  }

  loadPreset(url, displayName) {
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error("Network error");
        return res.json();
      })
      .then(data => {
        this.renderSceneData(data, displayName);
      })
      .catch(() => {
        console.log("Using embedded sample data.");
        this.renderSceneData(FALLBACK_SCENE, displayName);
      });
  }

  renderSceneData(sceneData, sourceName = "Loaded Model") {
    // Clear previous elements
    this.interactiveObjects.forEach(obj => this.scene.remove(obj));
    this.interactiveObjects = [];
    this.deselectObject();

    const objects = sceneData.objects || [];
    const bounds = sceneData.scene_metadata?.scene_bounds || { min: [0,0,0], max: [10,10,3] };

    // Center camera to scene bounding box
    const cx = (bounds.min[0] + bounds.max[0]) / 2;
    const cy = (bounds.min[1] + bounds.max[1]) / 2;
    const cz = (bounds.min[2] + bounds.max[2]) / 2;
    const span = Math.max(bounds.max[0] - bounds.min[0], bounds.max[1] - bounds.min[1], 10);

    this.controls.target.set(cx, cy, cz);
    this.camera.position.set(cx, cy - span * 1.2, cz + span * 0.9);
    this.controls.update();

    objects.forEach(item => {
      const geomData = item.geometry || {};
      const dims = geomData.dimensions || { width: 1, depth: 1, height: 1 };
      const trans = item.transform || {};
      const loc = trans.translation || { x: 0, y: 0, z: 0 };
      const rot = trans.rotation || { x: 0, y: 0, z: 0 };
      const matData = item.material || {};

      let geometry;
      if (geomData.primitive === "cylinder") {
        geometry = new THREE.CylinderGeometry(dims.width / 2, dims.width / 2, dims.height, 24);
        geometry.rotateX(Math.PI / 2);
      } else {
        geometry = new THREE.BoxGeometry(dims.width, dims.depth, dims.height);
      }

      const colorArr = matData.color || [0.8, 0.8, 0.8, 1.0];
      const isTransparent = colorArr.length > 3 && colorArr[3] < 1.0;

      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorArr[0], colorArr[1], colorArr[2]),
        roughness: matData.roughness ?? 0.6,
        metalness: matData.metallic ?? 0.0,
        transparent: isTransparent,
        opacity: isTransparent ? colorArr[3] : 1.0,
        wireframe: this.wireframeMode,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(loc.x, loc.y, loc.z);
      mesh.rotation.set(
        THREE.MathUtils.degToRad(rot.x),
        THREE.MathUtils.degToRad(rot.y),
        THREE.MathUtils.degToRad(rot.z)
      );

      mesh.castShadow = !isTransparent;
      mesh.receiveShadow = true;
      mesh.userData = item;
      this.scene.add(mesh);
      this.interactiveObjects.push(mesh);
    });

    document.getElementById("stat-count").textContent = objects.length;
    document.getElementById("stat-source").textContent = sourceName;
    document.getElementById("stat-generator").textContent = sceneData.scene_metadata?.generator || "Lane 2";
  }

  initEvents() {
    window.addEventListener("resize", () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // Raycast on click
    this.container.addEventListener("pointerdown", (e) => {
      this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.interactiveObjects);

      if (intersects.length > 0) {
        this.selectObject(intersects[0].object);
      } else {
        this.deselectObject();
      }
    });

    // File input handler (DXF, CSV, JSON, PNG, JPG via backend or local parse)
    const fileInput = document.getElementById("blueprint-file-input");
    const switcher = document.getElementById("blueprint-switcher");

    if (switcher) {
      switcher.addEventListener("change", (e) => {
        const item = this.loadedBlueprints.get(e.target.value);
        if (item) {
          this.renderSceneData(item.scene_data, e.target.value);
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", (e) => {
        const files = Array.from(e.target.files);
        this.processFiles(files);
      });
    }

    // Drag-and-drop onto viewer canvas / window
    window.addEventListener("dragover", (e) => e.preventDefault());
    window.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.processFiles(Array.from(e.dataTransfer.files));
      }
    });

    // Layer toggles
    document.getElementById("toggle-arch").addEventListener("change", (e) => {
      this.interactiveObjects.forEach(obj => {
        if (obj.userData.category === "architectural" && obj.userData.type !== "floor") {
          obj.visible = e.target.checked;
        }
      });
    });

    const toggleRooms = document.getElementById("toggle-rooms");
    if (toggleRooms) {
      toggleRooms.addEventListener("change", (e) => {
        this.interactiveObjects.forEach(obj => {
          if (obj.userData.type === "floor") obj.visible = e.target.checked;
        });
      });
    }

    document.getElementById("toggle-furn").addEventListener("change", (e) => {
      this.interactiveObjects.forEach(obj => {
        if (obj.userData.category === "furniture") obj.visible = e.target.checked;
      });
    });

    document.getElementById("toggle-wireframe").addEventListener("change", (e) => {
      this.wireframeMode = e.target.checked;
      this.interactiveObjects.forEach(obj => {
        obj.material.wireframe = this.wireframeMode;
      });
    });

    // Camera views
    document.getElementById("btn-view-3d").addEventListener("click", () => {
      this.controls.enableRotate = true;
      this.camera.up.set(0, 0, 1);
      this.controls.update();
      document.getElementById("btn-view-3d").classList.add("active");
      document.getElementById("btn-view-top").classList.remove("active");
    });

    document.getElementById("btn-view-top").addEventListener("click", () => {
      const target = this.controls.target;
      this.camera.position.set(target.x, target.y, target.z + 30);
      this.camera.up.set(0, 1, 0);
      this.controls.update();
      document.getElementById("btn-view-top").classList.add("active");
      document.getElementById("btn-view-3d").classList.remove("active");
    });

    // Preset buttons
    document.getElementById("btn-load-sample").addEventListener("click", () => {
      this.loadPreset("/api/sample", "Sample Floorplan (8 elements)");
    });

    document.getElementById("btn-load-legacy").addEventListener("click", () => {
      this.loadPreset("/api/legacy", "Legacy CAD Multileader (222 elements)");
    });

    const wireBtn = (id, url, label) => {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener("click", () => this.loadPreset(url, label));
    };

    wireBtn("btn-load-residential", "/api/residential", "Residential Flat (40 elements)");
    wireBtn("btn-load-studio", "/api/studio", "Studio Apartment (29 elements)");
    wireBtn("btn-load-twobhk", "/api/two-bhk", "2BHK Family Residence (57 elements)");
    wireBtn("btn-load-office", "/api/office", "Executive Office Suite (45 elements)");
    wireBtn("btn-load-synthetic", "/api/synthetic", "Synthetic 3-Room (28 elements)");
  }

  async processFiles(files) {
    const statusText = document.getElementById("upload-status");
    const switcherContainer = document.getElementById("blueprint-switcher-container");
    const switcher = document.getElementById("blueprint-switcher");

    if (!files || files.length === 0) return;

    statusText.textContent = files.length === 1
      ? `Processing ${files[0].name}...`
      : `Processing ${files.length} blueprints...`;

    let firstLoadedName = null;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      statusText.textContent = `Converting (${i + 1}/${files.length}): ${file.name}...`;

      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/api/convert", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP ${res.status}`);
        }

        const data = await res.json();
        if (data.success && data.scene_data) {
          this.loadedBlueprints.set(file.name, {
            scene_data: data.scene_data,
            element_count: data.element_count,
            duration_ms: data.duration_ms
          });
          if (!firstLoadedName) {
            firstLoadedName = file.name;
          }
        }
      } catch (err) {
        if (file.name.endsWith(".json")) {
          try {
            const text = await file.text();
            const data = JSON.parse(text);
            this.loadedBlueprints.set(file.name, {
              scene_data: data,
              element_count: (data.objects || []).length,
              duration_ms: 0
            });
            if (!firstLoadedName) firstLoadedName = file.name;
          } catch (e2) {
            console.error("Local JSON parse error:", e2);
          }
        } else {
          console.error("Conversion error on", file.name, err);
          statusText.textContent = `Error converting ${file.name}: ${err.message}`;
        }
      }
    }

    if (this.loadedBlueprints.size > 0) {
      if (switcher) {
        switcher.innerHTML = "";
        for (const [name, info] of this.loadedBlueprints.entries()) {
          const opt = document.createElement("option");
          opt.value = name;
          opt.textContent = `${name} (${info.element_count} items)`;
          switcher.appendChild(opt);
        }
      }

      if (switcherContainer) switcherContainer.style.display = "block";
      const activeName = firstLoadedName || Array.from(this.loadedBlueprints.keys())[0];
      if (switcher) switcher.value = activeName;
      const active = this.loadedBlueprints.get(activeName);
      this.renderSceneData(active.scene_data, activeName);
      statusText.textContent = `Ready! Loaded ${this.loadedBlueprints.size} blueprint(s). Active: ${activeName} (${active.element_count} items, ${active.duration_ms}ms)`;
    }
  }

  selectObject(mesh) {
    this.deselectObject();
    this.selectedMesh = mesh;
    this.prevColor = mesh.material.color.clone();
    mesh.material.color.setHex(0x2f81f7); // Highlight color

    const panel = document.getElementById("inspector-panel");
    const container = document.getElementById("inspector-content");
    const data = mesh.userData;

    let propsHtml = "";
    const props = data.properties || data.metadata;
    if (props && typeof props === "object") {
      for (const [k, v] of Object.entries(props)) {
        if (v !== null && v !== undefined && typeof v !== "object") {
          propsHtml += `<div class="prop-row"><span class="prop-key">${escapeHtml(k)}:</span><span class="prop-val">${escapeHtml(v)}</span></div>`;
        }
      }
    }

    container.innerHTML = `
      <div class="prop-row"><span class="prop-key">ID:</span><span class="prop-val">${escapeHtml(data.id)}</span></div>
      <div class="prop-row"><span class="prop-key">Name:</span><span class="prop-val">${escapeHtml(data.name || data.id)}</span></div>
      <div class="prop-row"><span class="prop-key">Type:</span><span class="prop-val">${escapeHtml(data.type)}</span></div>
      <div class="prop-row"><span class="prop-key">Category:</span><span class="prop-val">${escapeHtml(data.category)}</span></div>
      <div class="prop-row"><span class="prop-key">Dimensions:</span><span class="prop-val">W:${escapeHtml(data.geometry?.dimensions?.width)}m D:${escapeHtml(data.geometry?.dimensions?.depth)}m H:${escapeHtml(data.geometry?.dimensions?.height)}m</span></div>
      <div class="prop-row"><span class="prop-key">Position:</span><span class="prop-val">(${escapeHtml(data.transform?.translation?.x)}, ${escapeHtml(data.transform?.translation?.y)}, ${escapeHtml(data.transform?.translation?.z)})</span></div>
      ${propsHtml}
    `;
    panel.style.display = "block";
  }

  deselectObject() {
    if (this.selectedMesh && this.prevColor) {
      this.selectedMesh.material.color.copy(this.prevColor);
      this.selectedMesh = null;
    }
    document.getElementById("inspector-panel").style.display = "none";
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

// Instantiate viewer on DOM load
window.addEventListener("DOMContentLoaded", () => {
  new SceneViewer();
});
