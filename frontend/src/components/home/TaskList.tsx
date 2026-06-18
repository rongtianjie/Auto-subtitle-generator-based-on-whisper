import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TaskListCard } from '@/components/shared/TaskListCard';
import type { Task } from '@/types';

interface TaskListProps {
  tasks: Task[];
  isLoading: boolean;
  onRefresh?: () => void;
}

export function TaskList({ tasks, isLoading, onRefresh }: TaskListProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>最近任务</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-gray-500 py-8">
          加载中...
        </CardContent>
      </Card>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>最近任务</CardTitle>
          <CardDescription>暂无任务，创建一个开始吧</CardDescription>
        </CardHeader>
        <CardContent className="text-center text-gray-500 py-8">
          创建转录任务后，进度将实时显示在这里
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>最近任务</CardTitle>
        <CardDescription>你的最近 5 个任务</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskListCard key={task.id} task={task} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
