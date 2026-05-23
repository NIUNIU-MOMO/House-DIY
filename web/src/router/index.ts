import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/projects/:id/upload',
      name: 'floorplan-upload',
      component: () => import('../views/FloorPlanUploadView.vue'),
    },
    {
      path: '/projects/:id/parse',
      name: 'floorplan-parse',
      component: () => import('../views/FloorPlanParseView.vue'),
    },
    {
      path: '/projects/:id/editor',
      name: 'floorplan-editor',
      component: () => import('../views/FloorPlanEditorView.vue'),
    },
    {
      path: '/projects/:id/studio',
      name: 'design-studio',
      component: () => import('../views/DesignStudioView.vue'),
    },
    {
      path: '/projects/:id/generate',
      name: 'design-generate',
      component: () => import('../views/DesignGenerateView.vue'),
    },
    {
      path: '/projects/:id/gallery',
      name: 'render-gallery',
      component: () => import('../views/RenderGalleryView.vue'),
    },
    {
      path: '/projects/:id/delivery',
      name: 'delivery-overview',
      component: () => import('../views/DeliveryOverviewView.vue'),
    },
    {
      path: '/projects/:id/scene',
      name: 'scene-viewer',
      component: () => import('../views/SceneView.vue'),
    },
    {
      path: '/projects/:id/refine',
      name: 'design-refine',
      component: () => import('../views/DesignRefineView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
    {
      path: '/knowledge',
      name: 'knowledge-list',
      component: () => import('../views/KnowledgeListView.vue'),
    },
    {
      path: '/knowledge/import',
      name: 'knowledge-import',
      component: () => import('../views/KnowledgeImportView.vue'),
    },
  ],
})

export default router
