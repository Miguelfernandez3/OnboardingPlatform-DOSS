import { useEffect, useRef } from 'react';
import { QueryKey, useMutation, useQuery, UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';
import { useToast } from '../../infrastructure/notifications/useToast';
import { ApiError } from '../../infrastructure/api/errors/ApiError';

type QueryWithErrorOptions<
  TData,
  TError,
  TQueryKey extends QueryKey
> = UseQueryOptions<TData, TError, TData, TQueryKey> & {
  showErrorToast?: boolean;
  errorMessage?: string;
  onError?: (error: TError) => void;
};

/**
 * Hook que envuelve useQuery con manejo automático de errores
 */
export function useQueryWithError<
  TData,
  TError = ApiError,
  TQueryKey extends QueryKey = QueryKey
>(
  options: QueryWithErrorOptions<TData, TError, TQueryKey>
) {
  const { showApiError, showTranslated } = useToast();
  const { showErrorToast = true, errorMessage, onError, ...queryOptions } = options;
  const lastHandledErrorRef = useRef<unknown>(null);

  const queryResult = useQuery<TData, TError, TData, TQueryKey>({
    ...queryOptions,
  });

  useEffect(() => {
    const error = queryResult.error;
    if (!error || lastHandledErrorRef.current === error) {
      return;
    }

    lastHandledErrorRef.current = error;
    onError?.(error);

    if (showErrorToast) {
      if (errorMessage) {
        showTranslated(errorMessage, 'error');
      } else {
        showApiError(error);
      }
    }
  }, [queryResult.error, onError, showErrorToast, errorMessage, showTranslated, showApiError]);

  return queryResult;
}

/**
 * Hook que envuelve useMutation con manejo automático de errores
 */
export function useMutationWithError<TData, TVariables, TError = ApiError, TContext = unknown>(
  options: UseMutationOptions<TData, TError, TVariables, TContext> & {
    showErrorToast?: boolean;
    showSuccessToast?: boolean;
    errorMessage?: string;
    successMessage?: string;
  }
) {
  const { showApiError, showTranslated } = useToast();
  const {
    showErrorToast = true,
    showSuccessToast = false,
    errorMessage,
    successMessage,
    ...mutationOptions
  } = options;

  return useMutation<TData, TError, TVariables, TContext>({
    ...mutationOptions,
    onError: (error, variables, onMutateResult, context) => {
      // Llamar el onError original si existe
      if (mutationOptions.onError) {
        mutationOptions.onError(error, variables, onMutateResult, context);
      }

      // Mostrar toast si está habilitado
      if (showErrorToast) {
        if (errorMessage) {
          showTranslated(errorMessage, 'error');
        } else {
          showApiError(error);
        }
      }
    },
    onSuccess: (data, variables, onMutateResult, context) => {
      // Llamar el onSuccess original si existe
      if (mutationOptions.onSuccess) {
        mutationOptions.onSuccess(data, variables, onMutateResult, context);
      }

      // Mostrar toast de éxito si está habilitado
      if (showSuccessToast && successMessage) {
        showTranslated(successMessage, 'success');
      }
    },
  });
}
