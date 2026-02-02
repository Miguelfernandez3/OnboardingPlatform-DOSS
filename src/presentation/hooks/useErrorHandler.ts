import { useMutation, useQuery, UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';
import { useToast } from '../../infrastructure/notifications/useToast';
import { ApiError } from '../../infrastructure/api/errors/ApiError';

/**
 * Hook que envuelve useQuery con manejo automático de errores
 */
export function useQueryWithError<TData, TError = ApiError>(
  options: UseQueryOptions<TData, TError> & {
    showErrorToast?: boolean;
    errorMessage?: string;
  }
) {
  const { showApiError, showTranslated } = useToast();
  const { showErrorToast = true, errorMessage, ...queryOptions } = options;

  return useQuery<TData, TError>({
    ...queryOptions,
    onError: (error) => {
      // Llamar el onError original si existe
      if (queryOptions.onError) {
        queryOptions.onError(error);
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
  });
}

/**
 * Hook que envuelve useMutation con manejo automático de errores
 */
export function useMutationWithError<TData, TVariables, TError = ApiError>(
  options: UseMutationOptions<TData, TError, TVariables> & {
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

  return useMutation<TData, TError, TVariables>({
    ...mutationOptions,
    onError: (error, variables, context) => {
      // Llamar el onError original si existe
      if (mutationOptions.onError) {
        mutationOptions.onError(error, variables, context);
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
    onSuccess: (data, variables, context) => {
      // Llamar el onSuccess original si existe
      if (mutationOptions.onSuccess) {
        mutationOptions.onSuccess(data, variables, context);
      }

      // Mostrar toast de éxito si está habilitado
      if (showSuccessToast && successMessage) {
        showTranslated(successMessage, 'success');
      }
    },
  });
}
