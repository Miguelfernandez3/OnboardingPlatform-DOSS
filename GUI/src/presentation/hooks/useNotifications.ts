import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { notificationService } from '../../infrastructure/services/notificationService';

const PER_PAGE = 20;

/**
 * Listado paginado de notificaciones (sin leer o leídas) + mutaciones.
 */
export function useNotificationsList(readFilter: 'unread' | 'read', page: number) {
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: queryKeys.notifications.list(readFilter, page, PER_PAGE),
    queryFn: () => notificationService.getNotifications(page, PER_PAGE, undefined, readFilter),
    staleTime: 30_000
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => notificationService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    }
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    }
  });

  return {
    listQuery,
    markReadMutation,
    markAllReadMutation,
    notifications: listQuery.data?.notifications ?? [],
    totalPages: listQuery.data?.pagination.pages ?? 0,
    isLoading: listQuery.isLoading,
    isFetching: listQuery.isFetching,
    isError: listQuery.isError,
    error: listQuery.error
  };
}

/**
 * Total de notificaciones sin leer (endpoint dedicado COUNT en el servidor).
 */
export function useUnreadNotificationsCount(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.notifications.unreadCount,
    queryFn: () => notificationService.getUnreadCount(),
    staleTime: 1000 * 5, // 5 segundos
    refetchInterval: 1000 * 15, // 15 segundos
    enabled
  });
}
