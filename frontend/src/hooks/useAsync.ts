/**
 * Loading and UI state management utilities
 */
import { useState, useCallback } from 'react';

export interface LoadingState<T> {
  isLoading: boolean;
  error: string | null;
  data: T | null;
}

export function useAsync<T = unknown>() {
  const [state, setState] = useState<LoadingState<T>>({
    isLoading: false,
    error: null,
    data: null,
  });

  const execute = useCallback(async (asyncFunction: () => Promise<T>) => {
    setState({ isLoading: true, error: null, data: null });
    
    try {
      const data = await asyncFunction();
      setState({ isLoading: false, error: null, data });
      return data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred';
      setState({ isLoading: false, error: errorMessage, data: null });
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ isLoading: false, error: null, data: null });
  }, []);

  return {
    ...state,
    execute,
    reset,
  };
}

export interface AsyncOperationState {
  isLoading: boolean;
  error: string | null;
}

export function useAsyncOperation() {
  const [state, setState] = useState<AsyncOperationState>({
    isLoading: false,
    error: null,
  });

  const execute = useCallback(async <T>(operation: () => Promise<T>): Promise<T | null> => {
    setState({ isLoading: true, error: null });
    
    try {
      const result = await operation();
      setState({ isLoading: false, error: null });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Operation failed';
      setState({ isLoading: false, error: errorMessage });
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ isLoading: false, error: null });
  }, []);

  return {
    ...state,
    execute,
    reset,
  };
}
