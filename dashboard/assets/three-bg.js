// Lightweight Three.js animated background attached to #three-bg
(function(){
  if (typeof THREE === 'undefined') return;
  const host = document.getElementById('three-bg');
  if (!host) return;
  const canvas = document.createElement('canvas');
  host.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.set(0, 0, 6);
  const geometry = new THREE.IcosahedronGeometry(1.5, 1);
  const material = new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.5, metalness: 0.2, wireframe: true });
  const mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);
  const light1 = new THREE.DirectionalLight(0xffffff, 0.8); light1.position.set(3, 3, 5); scene.add(light1);
  const light2 = new THREE.AmbientLight(0x404040); scene.add(light2);
  function resize(){
    const w = host.clientWidth || window.innerWidth;
    const h = host.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();
  let rafId;
  function animate(){
    rafId = requestAnimationFrame(animate);
    mesh.rotation.x += 0.002;
    mesh.rotation.y += 0.003;
    renderer.render(scene, camera);
  }
  animate();
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { cancelAnimationFrame(rafId); }
    else { animate(); }
  });
})();
