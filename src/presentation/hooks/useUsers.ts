import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { userService } from '../../infrastructure/services/userService';
import { UserData, UserFilters } from '../../core/ports';

interface UseUsersReturn {
  users: UserData[];
  total: number;
  page: number;
  limit: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseUserReturn {
  user: UserData | null;
  loading: boolean;
  error: string | null;
}

/**
 * Hook para obtener la lista de usuarios con paginación
 */
export function useUsers(
  page: number = 1,
  limit: number = 10,
  filters?: UserFilters
): UseUsersReturn {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: queryKeys.users.all(page, limit, filters),
    queryFn: () => userService.getUsers(page, limit, filters),
    staleTime: 1000 * 30, // 30 segundos
  });

  return {
    users: data?.users || [],
    total: data?.total || 0,
    page: data?.page || page,
    limit: data?.limit || limit,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar usuarios' : null,
    refetch: () => {
      refetch();
    },
  };
}

/**
 * Hook para obtener un usuario por ID
 */
export function useUser(id: string): UseUserReturn {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: () => userService.getUser(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  return {
    user: data || null,
    loading: isLoading,
    error: isError ? (error as Error)?.message || 'Error al cargar usuario' : null,
  };
}

/**
 * Hook para crear un usuario
 */
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ email, password, role }: { email: string; password: string; role: string }) =>
      userService.createUser(email, password, role),
    onSuccess: () => {
      // Invalidar la lista de usuarios para refrescar
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
    },
  });
}

/**
 * Hook para actualizar el rol de un usuario
 */
export function useUpdateUserRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      userService.updateUserRole(id, role),
    onSuccess: (_, variables) => {
      // Invalidar la lista de usuarios y el usuario específico
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(variables.id) });
    },
  });
}

/**
 * Hook para eliminar un usuario
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => userService.deleteUser(id),
    onSuccess: () => {
      // Invalidar la lista de usuarios
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
    },
  });
}

/**
 * Hook para activar un usuario
 */
export function useActivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => userService.activateUser(id),
    onSuccess: (_, id) => {
      // Invalidar la lista de usuarios y el usuario específico
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
    },
  });
}
