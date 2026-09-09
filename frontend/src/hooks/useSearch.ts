import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { SearchResult, TextSearchRequest } from '@/types/api';

export function useTextSearch() {
  return useMutation<SearchResult[], Error, TextSearchRequest>({
    mutationFn: (payload) => api.post<SearchResult[]>('/search/text', payload),
  });
}

export interface ImageSearchPayload {
  file: File;
  aoi_id?: string;
  k?: number;
}

export function useImageSearch() {
  return useMutation<SearchResult[], Error, ImageSearchPayload>({
    mutationFn: ({ file, aoi_id, k = 12 }) => {
      const formData = new FormData();
      formData.append('file', file);
      if (aoi_id) formData.append('aoi_id', aoi_id);
      formData.append('k', String(k));
      return api.postFormData<SearchResult[]>('/search/image', formData);
    },
  });
}
