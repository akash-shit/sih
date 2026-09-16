const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: unknown;
      let errorMessage = `HTTP ${response.status} ${response.statusText}`;
      try {
        errorData = await response.json();
        if (typeof errorData === 'object' && errorData !== null && 'detail' in errorData) {
          const detail = (errorData as { detail: unknown }).detail;
          errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
        }
      } catch {
        // Body wasn't JSON, use status text
      }
      throw new ApiError(errorMessage, response.status, errorData);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network request failed',
      0,
      error
    );
  }
}

export const api = {
  baseUrl: API_BASE_URL,
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined | null>, signal?: AbortSignal): Promise<T> => {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
          searchParams.append(key, String(val));
        }
      });
      const query = searchParams.toString();
      if (query) {
        url += (url.includes('?') ? '&' : '?') + query;
      }
    }
    return request<T>(url, { method: 'GET', signal });
  },

  post: <T>(endpoint: string, body?: unknown): Promise<T> => {
    return request<T>(endpoint, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  postFormData: <T>(endpoint: string, formData: FormData): Promise<T> => {
    return request<T>(endpoint, {
      method: 'POST',
      body: formData,
    });
  },

  postFormDataBlob: async (endpoint: string, formData: FormData): Promise<Blob> => {
    const url = `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;
    const response = await fetch(url, { method: 'POST', body: formData });
    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status} ${response.statusText}`, response.status);
    }
    return response.blob();
  },

  /** Innovation endpoints are optional and additive to the original API. */
  sarObservations: <T = unknown>(tileId?: string): Promise<T> =>
    request<T>('/sar/observations' + (tileId ? `?tile_id=${encodeURIComponent(tileId)}` : '')),
  priorityChanges: <T = unknown>(limit = 24, aoiId?: string): Promise<T> =>
    api.get<T>('/changes/priority', { limit, aoi_id: aoiId }),
  aoiNarrative: <T = unknown>(aoiId: string): Promise<T> =>
    request<T>(`/aois/${encodeURIComponent(aoiId)}/narrative`),
};
