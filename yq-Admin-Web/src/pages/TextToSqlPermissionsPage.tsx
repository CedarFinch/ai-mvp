import { Badge, Button, Empty, Input, message, Modal, Segmented, Space, Spin, Switch, Tag, Tooltip, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { roleApi, textToSqlPermissionApi } from '../api/system';
import type {
  RoleItem,
  TextToSqlColumnGrant,
  TextToSqlColumnNode,
  TextToSqlSchemaDomain,
  TextToSqlTableNode,
} from '../types/system';

const { Text } = Typography;

const domainTone: Record<string, string> = {
  order: 'cyan',
  student: 'blue',
  teaching: 'green',
  learning: 'purple',
  homework: 'gold',
  exam: 'volcano',
  ai: 'geekblue',
};

export default function TextToSqlPermissionsPage() {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [schemaTree, setSchemaTree] = useState<TextToSqlSchemaDomain[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number>();
  const [selectedTableKey, setSelectedTableKey] = useState('');
  const [roleKeyword, setRoleKeyword] = useState('');
  const [tableKeyword, setTableKeyword] = useState('');
  const [onlyGranted, setOnlyGranted] = useState(false);
  const [grants, setGrants] = useState<Set<string>>(new Set());
  const [originalGrants, setOriginalGrants] = useState<Set<string>>(new Set());
  const [roleGrantCount, setRoleGrantCount] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [permissionLoading, setPermissionLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedRoleId) {
      loadRolePermission(selectedRoleId);
    }
  }, [selectedRoleId]);

  useEffect(() => {
    if (!selectedTableKey && schemaTree.length > 0) {
      const firstTable = schemaTree.flatMap((domain) => domain.tables)[0];
      if (firstTable) {
        setSelectedTableKey(tableKey(firstTable));
      }
    }
  }, [schemaTree, selectedTableKey]);

  const selectedRole = roles.find((role) => role.id === selectedRoleId);
  const selectedTable = useMemo(() => {
    return schemaTree.flatMap((domain) => domain.tables).find((table) => tableKey(table) === selectedTableKey);
  }, [schemaTree, selectedTableKey]);

  const visibleRoles = roles.filter((role) => {
    const keyword = roleKeyword.trim().toLowerCase();
    if (!keyword) {
      return true;
    }
    return role.roleCode.toLowerCase().includes(keyword) || role.roleName.toLowerCase().includes(keyword);
  });

  const filteredSchema = useMemo(() => {
    const keyword = tableKeyword.trim().toLowerCase();
    if (!keyword) {
      return schemaTree;
    }
    return schemaTree
      .map((domain) => ({
        ...domain,
        tables: domain.tables.filter(
          (table) =>
            table.tableName.toLowerCase().includes(keyword) ||
            (table.tableComment || '').toLowerCase().includes(keyword) ||
            table.columns.some((column) => column.columnName.toLowerCase().includes(keyword)),
        ),
      }))
      .filter((domain) => domain.tables.length > 0);
  }, [schemaTree, tableKeyword]);

  const visibleColumns = useMemo(() => {
    if (!selectedTable) {
      return [];
    }
    return selectedTable.columns.filter((column) => {
      if (onlyGranted && !grants.has(grantKey(column))) {
        return false;
      }
      return true;
    });
  }, [selectedTable, grants, onlyGranted]);

  const stats = useMemo(() => {
    const grantedColumns = Array.from(grants);
    const grantedDomains = new Set(grantedColumns.map((key) => key.split('|')[0]));
    const grantedTables = new Set(grantedColumns.map((key) => `${key.split('|')[0]}|${key.split('|')[1]}`));
    return {
      domains: grantedDomains.size,
      tables: grantedTables.size,
      columns: grantedColumns.length,
    };
  }, [grants]);

  const changes = useMemo(() => {
    const added = Array.from(grants).filter((key) => !originalGrants.has(key));
    const removed = Array.from(originalGrants).filter((key) => !grants.has(key));
    return { added, removed };
  }, [grants, originalGrants]);

  async function loadInitialData() {
    setLoading(true);
    try {
      const [rolePage, schema] = await Promise.all([
        roleApi.page({ pageNum: 1, pageSize: 200, status: 'ACTIVE' }),
        textToSqlPermissionApi.schemaTree(),
      ]);
      setRoles(rolePage.records);
      setSchemaTree(schema);
      if (rolePage.records[0]) {
        setSelectedRoleId(rolePage.records[0].id);
      }
      loadRoleGrantCounts(rolePage.records);
    } finally {
      setLoading(false);
    }
  }

  async function loadRoleGrantCounts(roleList: RoleItem[]) {
    const entries = await Promise.all(
      roleList.map(async (role) => {
        try {
          const detail = await textToSqlPermissionApi.rolePermission(role.id);
          return [role.id, detail.grants.length] as const;
        } catch {
          return [role.id, 0] as const;
        }
      }),
    );
    setRoleGrantCount(Object.fromEntries(entries));
  }

  async function loadRolePermission(roleId: number) {
    setPermissionLoading(true);
    try {
      const detail = await textToSqlPermissionApi.rolePermission(roleId);
      const nextGrants = new Set(detail.grants.filter((grant) => grant.granted).map(grantKey));
      setGrants(nextGrants);
      setOriginalGrants(new Set(nextGrants));
      setRoleGrantCount((prev) => ({ ...prev, [roleId]: nextGrants.size }));
    } finally {
      setPermissionLoading(false);
    }
  }

  function toggleColumn(column: TextToSqlColumnNode, checked: boolean) {
    setGrants((prev) => {
      const next = new Set(prev);
      const key = grantKey(column);
      if (checked) {
        next.add(key);
      } else {
        next.delete(key);
      }
      return next;
    });
  }

  function batchGrant(checked: boolean) {
    if (!selectedTable) {
      return;
    }
    setGrants((prev) => {
      const next = new Set(prev);
      for (const column of visibleColumns) {
        if (checked) {
          next.add(grantKey(column));
        } else {
          next.delete(grantKey(column));
        }
      }
      return next;
    });
  }

  function submitSave() {
    if (!selectedRoleId || !selectedRole) {
      return;
    }
    Modal.confirm({
      title: '保存 Text-to-SQL 数据权限',
      content: `角色 ${selectedRole.roleName} 将新增 ${changes.added.length} 个字段授权，移除 ${changes.removed.length} 个字段授权。`,
      okText: '保存',
      cancelText: '再看看',
      onOk: savePermission,
    });
  }

  async function savePermission() {
    if (!selectedRoleId) {
      return;
    }
    setSaving(true);
    try {
      await textToSqlPermissionApi.saveRolePermission(selectedRoleId, {
        grants: Array.from(grants).map(parseGrantKey),
      });
      setOriginalGrants(new Set(grants));
      setRoleGrantCount((prev) => ({ ...prev, [selectedRoleId]: grants.size }));
      message.success('Text-to-SQL 数据权限已保存');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="text-sql-permission-loading">
        <Spin />
      </div>
    );
  }

  return (
    <div className="text-sql-permission-page">
      <div className="text-sql-permission-head">
        <div>
          <h2>Text-to-SQL 权限</h2>
          <p>按角色控制可查询业务域、表和字段。</p>
        </div>
        <div className="text-sql-permission-stats">
          <Stat label="业务域" value={stats.domains} />
          <Stat label="表" value={stats.tables} />
          <Stat label="字段" value={stats.columns} />
        </div>
      </div>

      <div className="text-sql-permission-workbench">
        <section className="text-sql-role-panel">
          <PanelTitle title="角色" extra={`${roles.length} 个`} />
          <Input.Search allowClear placeholder="搜索角色编码/名称" value={roleKeyword} onChange={(e) => setRoleKeyword(e.target.value)} />
          <div className="text-sql-role-list">
            {visibleRoles.map((role) => {
              const configured = (roleGrantCount[role.id] || 0) > 0;
              return (
                <button
                  key={role.id}
                  className={`text-sql-role-item ${role.id === selectedRoleId ? 'is-active' : ''}`}
                  onClick={() => setSelectedRoleId(role.id)}
                >
                  <span>
                    <strong>{role.roleName}</strong>
                    <code>{role.roleCode}</code>
                  </span>
                  <Tag color={configured ? 'success' : 'default'}>{configured ? '已配置' : '未配置'}</Tag>
                </button>
              );
            })}
            {visibleRoles.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配角色" />}
          </div>
        </section>

        <section className="text-sql-schema-panel">
          <PanelTitle title="业务域 / 表" extra={`${schemaTree.flatMap((domain) => domain.tables).length} 张表`} />
          <Input.Search allowClear placeholder="搜索表名、说明、字段" value={tableKeyword} onChange={(e) => setTableKeyword(e.target.value)} />
          <div className="text-sql-domain-list">
            {filteredSchema.map((domain) => (
              <div className="text-sql-domain-block" key={domain.businessDomain}>
                <div className="text-sql-domain-title">
                  <Tag color={domainTone[domain.businessDomain] || 'default'}>{domain.businessDomain}</Tag>
                  <strong>{domain.businessDomainName}</strong>
                  <Text type="secondary">{domain.tables.length} 张表</Text>
                </div>
                {domain.tables.map((table) => {
                  const grantedCount = table.columns.filter((column) => grants.has(grantKey(column))).length;
                  return (
                    <button
                      key={tableKey(table)}
                      className={`text-sql-table-item ${tableKey(table) === selectedTableKey ? 'is-active' : ''}`}
                      onClick={() => setSelectedTableKey(tableKey(table))}
                    >
                      <span>
                        <strong>{table.tableName}</strong>
                        <em>{table.tableComment || '暂无说明'}</em>
                      </span>
                      <Badge count={`${grantedCount}/${table.columns.length}`} color={grantedCount ? '#13c2c2' : '#d9d9d9'} />
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </section>

        <section className="text-sql-field-panel">
          <div className="text-sql-field-head">
            <div>
              <Text type="secondary">当前角色</Text>
              <h3>{selectedRole ? selectedRole.roleName : '请选择角色'}</h3>
            </div>
          </div>

          {selectedTable ? (
            <Spin spinning={permissionLoading}>
              <div className="text-sql-selected-table">
                <Tag color={domainTone[selectedTable.businessDomain] || 'default'}>{selectedTable.businessDomain}</Tag>
                <strong>{selectedTable.tableName}</strong>
                <span>{selectedTable.tableComment || '暂无表说明'}</span>
              </div>

              <div className="text-sql-field-toolbar">
                <Segmented
                  value={onlyGranted ? 'granted' : 'all'}
                  onChange={(value) => {
                    setOnlyGranted(value === 'granted');
                  }}
                  options={[
                    { label: '全部字段', value: 'all' },
                    { label: '已授权', value: 'granted' },
                  ]}
                />
                <Space>
                  <Button onClick={() => batchGrant(true)}>批量授权</Button>
                  <Button onClick={() => batchGrant(false)}>批量取消</Button>
                </Space>
              </div>

              <div className="text-sql-column-list">
                {visibleColumns.map((column) => (
                  <div className="text-sql-column-row" key={grantKey(column)}>
                    <div>
                      <Space>
                        <strong>{column.columnName}</strong>
                      </Space>
                      <p>{column.columnComment || '暂无字段说明'}</p>
                    </div>
                    <Tooltip title="控制当前角色是否可以在 Text-to-SQL 中使用该字段">
                      <Switch
                        checked={grants.has(grantKey(column))}
                        onChange={(checked) => toggleColumn(column, checked)}
                      />
                    </Tooltip>
                  </div>
                ))}
                {visibleColumns.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配字段" />}
              </div>

              <div className="text-sql-save-bar">
                <div>
                  <strong>变更摘要</strong>
                  <span>新增 {changes.added.length} 个，移除 {changes.removed.length} 个</span>
                </div>
                <Button type="primary" loading={saving} disabled={!selectedRoleId} onClick={submitSave}>
                  保存配置
                </Button>
              </div>
            </Spin>
          ) : (
            <Empty description="请选择一张表" />
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function PanelTitle({ title, extra }: { title: string; extra: string }) {
  return (
    <div className="text-sql-panel-title">
      <strong>{title}</strong>
      <span>{extra}</span>
    </div>
  );
}

function tableKey(table: TextToSqlTableNode) {
  return `${table.businessDomain}|${table.tableName}`;
}

function grantKey(value: TextToSqlColumnNode | TextToSqlColumnGrant) {
  return `${value.businessDomain}|${value.tableName}|${value.columnName}`;
}

function parseGrantKey(key: string): TextToSqlColumnGrant {
  const [businessDomain, tableName, columnName] = key.split('|');
  return { businessDomain, tableName, columnName, granted: true };
}
